import unittest

import main


class MainBackendLabelTests(unittest.TestCase):
    def test_backend_labels_are_korean_and_map_to_config_values(self):
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["테스트 번역기"], "local_dummy")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["Papago API"], "papago")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["번역 비활성화"], "disabled")

    def test_backend_value_to_label_round_trip(self):
        for label, value in main.BACKEND_LABEL_TO_VALUE.items():
            self.assertEqual(main.BACKEND_VALUE_TO_LABEL[value], label)


if __name__ == "__main__":
    unittest.main()
