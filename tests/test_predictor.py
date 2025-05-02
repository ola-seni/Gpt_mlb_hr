# tests/test_predictor.py
import unittest
import pandas as pd
from predictor import generate_hr_predictions

class TestPredictor(unittest.TestCase):
    
    def test_generate_hr_predictions_empty_df(self):
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        result = generate_hr_predictions(empty_df)
        self.assertTrue(result.empty)
    
    def test_generate_hr_predictions_basic_functionality(self):
        # Create a minimal test DataFrame that works with your implementation
        test_data = pd.DataFrame({
            'ISO': [0.250, 0.180],
            'barrel_rate_50': [0.15, 0.08],
            'hr_per_9': [1.2, 0.8]
        })
        
        # Add any additional required columns
        test_data['pitch_matchup_score'] = 0.0
        test_data['bullpen_boost'] = 0.0
        
        # Try to run the function
        try:
            result = generate_hr_predictions(test_data)
            
            # Only run these checks if the function succeeded
            self.assertIn('HR_Score', result.columns)
            if len(result) > 1:
                self.assertGreaterEqual(result['HR_Score'].iloc[0], result['HR_Score'].iloc[1])
        except Exception as e:
            self.fail(f"generate_hr_predictions raised {type(e).__name__} unexpectedly: {e}")

if __name__ == '__main__':
    unittest.main()
