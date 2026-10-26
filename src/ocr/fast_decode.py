"""Greedy VietOCR Transformer inference with per-layer attention caches.

Uses the existing weights and causal attention. Each decoding step computes only
the new token, keeping the self-attention keys/values from previous steps.
"""
from math import sqrt
from collections import defaultdict

import torch
from torch.nn import functional as F


def _project(attention, value, index):
    size = attention.embed_dim
    bias = attention.in_proj_bias
    return F.linear(value, attention.in_proj_weight[index * size:(index + 1) * size],
                    None if bias is None else bias[index * size:(index + 1) * size])


def _heads(value, attention):
    length, batch, size = value.shape
    return value.reshape(length, batch, attention.num_heads, size // attention.num_heads).permute(1, 2, 0, 3)


def _attend(attention, query, keys, values):
    query = _heads(_project(attention, query, 0), attention)
    output = F.scaled_dot_product_attention(query, keys, values, dropout_p=0.0)
    batch, _, length, _ = output.shape
    output = output.permute(2, 0, 1, 3).reshape(length, batch, attention.embed_dim)
    return attention.out_proj(output)


def greedy_decode(images, model, max_seq_length=128):
    """Return token IDs and mean character scores, stopping at EOS per image."""
    model.eval()
    transformer = model.transformer
    decoder = transformer.transformer.decoder
    with torch.inference_mode():
        memory = transformer.forward_encoder(model.cnn(images))
        cached = []
        for layer in decoder.layers:
            if layer.norm_first or not layer.self_attn._qkv_same_embed_dim:
                raise ValueError("Unsupported Transformer decoder configuration")
            cross = layer.multihead_attn
            cached.append({"self_k": None, "self_v": None,
                           "memory_k": _heads(_project(cross, memory, 1), cross),
                           "memory_v": _heads(_project(cross, memory, 2), cross)})
        batch = images.shape[0]
        token = torch.ones(batch, dtype=torch.long, device=images.device)
        finished = torch.zeros(batch, dtype=torch.bool, device=images.device)
        totals = torch.zeros(batch, device=images.device)
        counts = torch.zeros(batch, device=images.device)
        sequences = [[1] for _ in range(batch)]
        # Upstream translate() also permits max_seq_length + 1 steps.
        for step in range(max_seq_length + 1):
            hidden = transformer.embed_tgt(token).unsqueeze(0) * sqrt(transformer.d_model)
            hidden = hidden + transformer.pos_enc.pe[step:step + 1]
            for layer, cache in zip(decoder.layers, cached):
                attention = layer.self_attn
                keys = _heads(_project(attention, hidden, 1), attention)
                values = _heads(_project(attention, hidden, 2), attention)
                if cache["self_k"] is not None:
                    keys = torch.cat((cache["self_k"], keys), dim=2)
                    values = torch.cat((cache["self_v"], values), dim=2)
                cache["self_k"], cache["self_v"] = keys, values
                hidden = layer.norm1(hidden + _attend(attention, hidden, keys, values))
                hidden = layer.norm2(hidden + _attend(layer.multihead_attn, hidden,
                                                     cache["memory_k"], cache["memory_v"]))
                feedforward = layer.linear2(layer.activation(layer.linear1(hidden)))
                hidden = layer.norm3(hidden + feedforward)
            if decoder.norm is not None:
                hidden = decoder.norm(hidden)
            probabilities = transformer.fc(hidden[0]).softmax(dim=-1)
            probability, token = probabilities.max(dim=-1)
            active_character = ~finished & (token > 3)
            totals += probability * active_character
            counts += active_character
            for index, value in enumerate(token.tolist()):
                if not finished[index]:
                    sequences[index].append(value)
            finished |= token == 2
            if bool(finished.all()):
                break
        return sequences, (totals / counts.clamp_min(1)).tolist()


class CachedVietOCR:
    """Predictor-compatible adapter; preprocessing and vocabulary stay unchanged."""
    def __init__(self, predictor):
        self.config = predictor.config
        self.model = predictor.model
        self.vocab = predictor.vocab
        self.device = predictor.device

    def predict(self, image, return_prob=False):
        texts, scores = self.predict_batch([image], return_prob=True)
        return (texts[0], scores[0]) if return_prob else texts[0]

    def predict_batch(self, images, return_prob=False, batch_size=8):
        from vietocr.tool.translate import process_input
        dataset = self.config["dataset"]
        buckets = defaultdict(list)
        for index, image in enumerate(images):
            pixels = process_input(image, dataset["image_height"], dataset["image_min_width"],
                                   dataset["image_max_width"])
            buckets[pixels.shape[-1]].append((index, pixels))
        texts, scores = [""] * len(images), [0.0] * len(images)
        for bucket in buckets.values():
            for start in range(0, len(bucket), batch_size):
                items = bucket[start:start + batch_size]
                pixels = torch.cat([value for _, value in items]).to(self.device)
                sequences, probabilities = greedy_decode(pixels, self.model)
                for (index, _), sequence, score in zip(items, sequences, probabilities):
                    texts[index], scores[index] = self.vocab.decode(sequence), score
        return (texts, scores) if return_prob else texts
