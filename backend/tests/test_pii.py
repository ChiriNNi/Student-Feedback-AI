import unittest

from app.nlp.pii import mask_pii_report, names_pattern


class PiiMaskingTests(unittest.TestCase):
    def setUp(self):
        self.names = names_pattern([
            "Dr. Aigerim Nurlanovna",
            "Алексей Иванов",
            "Александр Петров",
            "Айгерім Сәрсенова",
        ])

    def assertMasked(self, text):
        masked, removed = mask_pii_report(text, self.names)
        self.assertIn("[NAME]", masked, masked)
        self.assertGreaterEqual(removed["NAME"], 1)

    def test_exact_names_are_removed(self):
        for text in ("Aigerim explains well", "Алексей помог", "Айгерім апай жақсы"):
            with self.subTest(text=text):
                self.assertMasked(text)

    def test_case_and_small_typo_are_removed(self):
        for text in ("aigerim explains well", "Алексея помог", "Александрр объяснил"):
            with self.subTest(text=text):
                self.assertMasked(text)

    def test_repeated_letter_obfuscation_is_removed(self):
        for text in ("АААлександр объяснил", "Аааайгерим помогла", "Aiiigerim answered"):
            with self.subTest(text=text):
                self.assertMasked(text)

    def test_mixed_scripts_are_removed(self):
        for text in ("Айгерим объяснила", "Айгерім түсіндірді", "Aигерим помогла"):
            with self.subTest(text=text):
                self.assertMasked(text)

    def test_email_phone_and_ids_are_removed(self):
        masked, removed = mask_pii_report(
            "alex@example.kz, +7 701 555 12 34, ID 240103083 and 990101123456",
            self.names,
        )
        self.assertIn("[EMAIL]", masked)
        self.assertIn("[PHONE]", masked)
        self.assertEqual(removed["ID"], 2)

    def test_ordinary_words_and_years_survive(self):
        masked, _ = mask_pii_report("The material was clear in 2025 and 2026.", self.names)
        self.assertEqual(masked, "The material was clear in 2025 and 2026.")


class LookAlikeWordTests(unittest.TestCase):
    """Short names must not eat everyday words that are one typo away from them."""

    def setUp(self):
        self.names = names_pattern(["Dana Akhmetova", "Bolat Serikov", "Mark Lee", "Grace Kim"])

    def test_everyday_words_survive(self):
        for text in (
            "The data was fine, but the bolt in the lab was broken.",
            "Data was fine. Bolt was broken.",
            "The market analysis task was good; mark distribution was fair.",
            "Market research was the best part.",
            "Danger: the dates for the exam changed twice.",
            "Grace period for deadlines would help.",
        ):
            with self.subTest(text=text):
                masked, removed = mask_pii_report(text, self.names)
                self.assertEqual(masked, text)
                self.assertFalse(removed)

    def test_names_are_still_removed(self):
        for text in (
            "Dana explained everything.",
            "I asked Dana for help.",
            "Bolat was always on time.",
            "Our TA Bolatt was great.",
            "Thanks to Mark and Grace for the labs.",
            "Марка все уважают.",
            "Akhmetova grades fairly.",
        ):
            with self.subTest(text=text):
                masked, removed = mask_pii_report(text, self.names)
                self.assertGreaterEqual(removed["NAME"], 1, masked)


if __name__ == "__main__":
    unittest.main()
