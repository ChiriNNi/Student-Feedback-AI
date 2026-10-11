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


if __name__ == "__main__":
    unittest.main()
