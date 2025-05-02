# tests/test_utils.py
import unittest
from utils import generate_game_id

class TestUtils(unittest.TestCase):
    
    def test_generate_game_id(self):
        # Test basic functionality
        game_id = generate_game_id("Aaron Judge", "Gerrit Cole", "2025-05-01")
        self.assertEqual(game_id, "aaron_judge__vs__gerrit_cole__2025-05-01")
        
        # Test handling of special characters
        game_id = generate_game_id("Ronald Acuña Jr.", "Max Scherzer", "2025-05-01")
        self.assertEqual(game_id, "ronald_acuna__vs__max_scherzer__2025-05-01")

if __name__ == '__main__':
    unittest.main()
