import unittest

from app.lexicon import interpret_claim


class AmbiguityLexiconTests(unittest.TestCase):
    def test_roman_urdu_teeka_is_ambiguous(self):
        result = interpret_claim("teeka se dard kam hota hai")
        self.assertTrue(result["ambiguity_detected"])
        self.assertEqual(result["topic"], "ambiguous")
        self.assertIn("vaccine/immunization", result["possible_meanings"])
        self.assertIn("injection", result["possible_meanings"])

    def test_urdu_tika_is_ambiguous(self):
        result = interpret_claim("ٹیکہ لگانے سے درد کم ہوتا ہے")
        self.assertTrue(result["ambiguity_detected"])

    def test_vaccine_context_disambiguates_teekay(self):
        result = interpret_claim("teekay bachon ko polio se bachate hain")
        self.assertFalse(result["ambiguity_detected"])
        self.assertEqual(result["topic"], "vaccination")

    def test_injection_context_disambiguates_tikka(self):
        result = interpret_claim("dard ka tikka lagane se araam milta hai")
        self.assertFalse(result["ambiguity_detected"])
        self.assertEqual(result["topic"], "injection")


if __name__ == "__main__":
    unittest.main()
