import unittest


class FastDecodeTests(unittest.TestCase):
    def test_cache_matches_upstream_causal_decoder_for_a_batch(self):
        import numpy as np
        import torch
        from vietocr.model.seqmodel.transformer import LanguageTransformer
        from vietocr.tool.translate import translate
        from src.ocr.fast_decode import greedy_decode

        torch.manual_seed(71)
        torch.set_num_threads(2)

        class TinyOCR(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.transformer = LanguageTransformer(10, 8, 2, 1, 2, 16, 32, 0, 0)
                with torch.no_grad():
                    self.transformer.fc.bias[:4] = -100

            def cnn(self, images):
                return images.mean(dim=2).permute(2, 0, 1)

        model = TinyOCR()
        images = torch.rand(2, 8, 1, 6)
        expected, scores = translate(images, model, max_seq_length=8)
        actual, actual_scores = greedy_decode(images, model, max_seq_length=8)
        self.assertEqual(actual, expected.tolist())
        np.testing.assert_allclose(actual_scores, scores, rtol=0.00001, atol=0.000001)


if __name__ == "__main__":
    unittest.main()
