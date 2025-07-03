"""
Learning module for the Cainiao Parcel Station LTO system.

This module implements the "Learning" component of the LTO framework.
Currently uses rule-based prediction, but designed to be easily replaceable
with machine learning models (e.g., Logistic Regression) in the future.

The learning module predicts pickup probability (p_hat_i) for each parcel
based on features like arrival time, parcel size, and time period.
"""

import random
from datetime import datetime
from typing import Dict, Any

from data_structures import Parcel, ParcelSize
import config


class PickupProbabilityPredictor:
    """
    Predicts the probability that a parcel will be picked up within a certain timeframe.
    
    This is the core "Learning" component of the LTO system. Currently implements
    a rule-based approach, but can be extended with ML models.
    """
    
    def __init__(self, use_noise: bool = True):
        """
        Initialize the predictor.
        
        Args:
            use_noise: Whether to add random noise to predictions for realism
        """
        self.use_noise = use_noise
        if config.RANDOM_SEED is not None:
            random.seed(config.RANDOM_SEED)
    
    def predict_pickup_probability(self, parcel: Parcel, current_time: datetime) -> float:
        """
        Predict the probability that a parcel will be picked up.
        
        This is the main function that implements the learning component.
        Currently uses rule-based logic but can be replaced with ML models.
        
        Args:
            parcel: The parcel to predict for
            current_time: Current simulation time
            
        Returns:
            Predicted pickup probability (0.0 to 1.0)
        """
        # Extract features from the parcel and current context
        features = self._extract_features(parcel, current_time)
        
        # Apply rule-based prediction logic
        probability = self._rule_based_prediction(features)
        
        # Add noise if enabled (to simulate prediction uncertainty)
        if self.use_noise:
            probability = self._add_noise(probability)
        
        # Ensure probability is within valid range
        probability = max(config.MIN_PROBABILITY, min(config.MAX_PROBABILITY, probability))
        
        return probability
    
    def _extract_features(self, parcel: Parcel, current_time: datetime) -> Dict[str, Any]:
        """
        Extract features from parcel and context for prediction.
        
        This function defines what information the learning model uses.
        In a real ML implementation, these would be the input features.
        
        Args:
            parcel: The parcel to extract features from
            current_time: Current simulation time
            
        Returns:
            Dictionary of features
        """
        arrival_hour = parcel.arrival_time.hour
        time_period = config.get_time_period(arrival_hour)
        
        # Calculate time since arrival (in hours)
        time_since_arrival = (current_time - parcel.arrival_time).total_seconds() / 3600
        
        features = {
            'arrival_hour': arrival_hour,
            'time_period': time_period,
            'parcel_size': parcel.size,
            'time_since_arrival': time_since_arrival,
            'is_peak_time': time_period in ['peak_morning', 'peak_afternoon', 'peak_evening'],
            'is_weekend': False,  # Placeholder - could be extended
            'is_holiday': False   # Placeholder - could be extended
        }
        
        return features
    
    def _rule_based_prediction(self, features: Dict[str, Any]) -> float:
        """
        Apply rule-based logic to predict pickup probability.
        
        This implements the simplified learning approach described in your plan.
        The rules are based on time periods and parcel characteristics.
        
        Args:
            features: Extracted features dictionary
            
        Returns:
            Base probability before noise
        """
        # Start with base probability for the time period
        time_period = features['time_period']
        base_prob = config.BASE_PICKUP_PROBABILITIES.get(time_period, 0.5)
        
        # Apply size modifier
        size_modifier = config.SIZE_PROBABILITY_MODIFIERS.get(features['parcel_size'], 1.0)
        probability = base_prob * size_modifier
        
        # Apply time-since-arrival modifier
        # Assumption: Probability decreases slightly as time passes without pickup
        time_since_arrival = features['time_since_arrival']
        if time_since_arrival > 2:  # After 2 hours
            time_decay = max(0.8, 1.0 - (time_since_arrival - 2) * 0.05)
            probability *= time_decay
        
        # Boost probability during peak times
        if features['is_peak_time']:
            probability *= 1.1  # 10% boost during peak times
        
        return probability
    
    def _add_noise(self, probability: float) -> float:
        """
        Add random noise to the probability prediction.
        
        This simulates the uncertainty inherent in real-world predictions.
        
        Args:
            probability: Base probability
            
        Returns:
            Probability with added noise
        """
        noise = random.uniform(-config.PROBABILITY_NOISE_RANGE, config.PROBABILITY_NOISE_RANGE)
        return probability + noise
    
    def get_prediction_explanation(self, parcel: Parcel, current_time: datetime) -> str:
        """
        Get a human-readable explanation of the prediction.
        
        Useful for debugging and understanding the learning logic.
        
        Args:
            parcel: The parcel that was predicted for
            current_time: Current simulation time
            
        Returns:
            Explanation string
        """
        features = self._extract_features(parcel, current_time)
        base_prob = config.BASE_PICKUP_PROBABILITIES.get(features['time_period'], 0.5)
        size_modifier = config.SIZE_PROBABILITY_MODIFIERS.get(features['parcel_size'], 1.0)
        
        explanation = (
            f"Parcel {parcel.parcel_id}: "
            f"Time period '{features['time_period']}' (base prob: {base_prob:.2f}), "
            f"Size {features['parcel_size'].value} (modifier: {size_modifier:.2f}), "
            f"Peak time: {features['is_peak_time']}"
        )
        
        return explanation


class MLPickupPredictor(PickupProbabilityPredictor):
    """
    Placeholder for future machine learning-based predictor.
    
    This class shows how the rule-based predictor could be replaced
    with a trained ML model (e.g., Logistic Regression) while maintaining
    the same interface.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize ML predictor.
        
        Args:
            model_path: Path to trained model file (placeholder)
        """
        super().__init__(use_noise=False)  # ML models have inherent uncertainty
        self.model = None  # Placeholder for trained model
        self.model_path = model_path
        
        # In a real implementation, you would load the trained model here:
        # self.model = joblib.load(model_path)
    
    def predict_pickup_probability(self, parcel: Parcel, current_time: datetime) -> float:
        """
        Predict using trained ML model.
        
        This is a placeholder implementation. In reality, you would:
        1. Extract and preprocess features
        2. Use the trained model to predict
        3. Return the probability
        """
        # For now, fall back to rule-based prediction
        # In future: return self.model.predict_proba(features)[0][1]
        return super().predict_pickup_probability(parcel, current_time)
    
    def train_model(self, training_data: list):
        """
        Placeholder for model training functionality.
        
        Args:
            training_data: List of (features, label) tuples
        """
        # Placeholder for training logic
        # In reality, this would implement:
        # 1. Data preprocessing
        # 2. Feature engineering
        # 3. Model training (e.g., LogisticRegression.fit())
        # 4. Model validation
        # 5. Model saving
        pass


def create_predictor(predictor_type: str = "rule_based") -> PickupProbabilityPredictor:
    """
    Factory function to create the appropriate predictor.
    
    Args:
        predictor_type: Type of predictor ("rule_based" or "ml")
        
    Returns:
        Configured predictor instance
    """
    if predictor_type == "rule_based":
        return PickupProbabilityPredictor()
    elif predictor_type == "ml":
        return MLPickupPredictor()
    else:
        raise ValueError(f"Unknown predictor type: {predictor_type}")


# Example usage and testing
if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    # Create a test predictor
    predictor = create_predictor("rule_based")
    
    # Create test parcels
    current_time = datetime(2024, 6, 10, 9, 0)  # 9:00 AM
    
    test_parcels = [
        Parcel("P001", current_time - timedelta(minutes=30), ParcelSize.SMALL),
        Parcel("P002", current_time - timedelta(hours=1), ParcelSize.MEDIUM),
        Parcel("P003", current_time - timedelta(minutes=15), ParcelSize.LARGE),
    ]
    
    # Test predictions
    print("Testing Learning Module:")
    print("=" * 50)
    
    for parcel in test_parcels:
        prob = predictor.predict_pickup_probability(parcel, current_time)
        explanation = predictor.get_prediction_explanation(parcel, current_time)
        
        print(f"Prediction: {prob:.3f}")
        print(f"Explanation: {explanation}")
        print("-" * 30)
    
    print("Learning module test completed!") 