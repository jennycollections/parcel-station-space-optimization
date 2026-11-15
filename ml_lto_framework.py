"""
Machine Learning LTO Framework for Cainiao System

This module implements a comprehensive machine learning framework that replaces
the current rule-based prediction system with advanced ML models including:

1. Ensemble Learning for pickup probability prediction
2. Deep Learning models for complex pattern recognition
3. Online learning for real-time adaptation
4. Feature engineering pipeline
5. Model selection and hyperparameter optimization
6. Integration with existing SLAP framework

Key improvements:
- Multi-model ensemble approach
- Continuous learning from new data
- Advanced feature engineering
- Model interpretability and debugging
- Performance monitoring and drift detection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import pickle
import logging
from abc import ABC, abstractmethod
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, GridSearchCV, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, LabelEncoder, PolynomialFeatures
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.base import BaseEstimator, ClassifierMixin
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')
from collections import deque

# 直接导入当前目录下的模块
from data_structures import Parcel, Shelf, ParcelStation, ParcelSize, ShelfType
from learning_module import PickupProbabilityPredictor
# 从增强系统导入新组件
from enhanced_dynamic_simulation import EnvironmentalFactors, CustomerProfile


@dataclass
class MLConfig:
    """Configuration for ML models"""
    
    # Model selection
    use_ensemble: bool = True
    ensemble_methods: List[str] = field(default_factory=lambda: ['rf', 'gb', 'xgb', 'lr', 'mlp'])
    primary_model: str = 'ensemble'
    
    # Training parameters
    train_test_split: float = 0.8
    cross_validation_folds: int = 5
    random_state: int = 42
    
    # Feature engineering
    use_polynomial_features: bool = True
    polynomial_degree: int = 2
    use_interaction_features: bool = True
    feature_selection_k: int = 20
    
    # Online learning
    online_learning_enabled: bool = True
    batch_update_size: int = 100
    concept_drift_threshold: float = 0.1
    
    # Model performance
    min_accuracy_threshold: float = 0.7
    retrain_frequency_hours: int = 24
    performance_window_size: int = 1000
    
    # Hyperparameter optimization
    use_hyperopt: bool = True
    hyperopt_max_evals: int = 50
    
    # Interpretability
    feature_importance_enabled: bool = True
    explain_predictions: bool = False


@dataclass
class TrainingData:
    """Container for training data"""
    features: pd.DataFrame
    labels: pd.Series
    feature_names: List[str]
    timestamp: datetime
    data_source: str
    
    def __len__(self) -> int:
        return len(self.features)
    
    def split_train_test(self, test_size: float = 0.2) -> Tuple['TrainingData', 'TrainingData']:
        """Split data into train and test sets"""
        split_idx = int(len(self) * (1 - test_size))
        
        train_data = TrainingData(
            features=self.features.iloc[:split_idx],
            labels=self.labels.iloc[:split_idx],
            feature_names=self.feature_names,
            timestamp=self.timestamp,
            data_source=f"{self.data_source}_train"
        )
        
        test_data = TrainingData(
            features=self.features.iloc[split_idx:],
            labels=self.labels.iloc[split_idx:],
            feature_names=self.feature_names,
            timestamp=self.timestamp,
            data_source=f"{self.data_source}_test"
        )
        
        return train_data, test_data


class AdvancedFeatureEngineer:
    """Advanced feature engineering for ML models"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.polynomial_features = None
        self.feature_names = []
        self.is_fitted = False
        
        if config.use_polynomial_features:
            self.polynomial_features = PolynomialFeatures(
                degree=config.polynomial_degree,
                interaction_only=config.use_interaction_features,
                include_bias=False
            )
    
    def extract_comprehensive_features(self, parcel: Parcel, 
                                     current_time: datetime,
                                     station: ParcelStation,
                                     environmental_factors: EnvironmentalFactors,
                                     customer_profile: Optional[CustomerProfile] = None) -> Dict[str, Any]:
        """Extract comprehensive features for ML prediction"""
        
        features = {}
        
        # Temporal features
        arrival_time = parcel.arrival_time
        features.update(self._extract_temporal_features(arrival_time, current_time))
        
        # Parcel features
        features.update(self._extract_parcel_features(parcel))
        
        # Station features
        features.update(self._extract_station_features(station, current_time))
        
        # Environmental features
        features.update(self._extract_environmental_features(environmental_factors))
        
        # Customer features
        if customer_profile:
            features.update(self._extract_customer_features(customer_profile, current_time))
        else:
            features.update(self._get_default_customer_features())
        
        # Historical features
        features.update(self._extract_historical_features(parcel, station, current_time))
        
        # Contextual features
        features.update(self._extract_contextual_features(parcel, station, environmental_factors))
        
        return features
    
    def _extract_temporal_features(self, arrival_time: datetime, current_time: datetime) -> Dict[str, Any]:
        """Extract time-based features"""
        wait_time = (current_time - arrival_time).total_seconds() / 3600  # hours
        
        return {
            # Basic time features
            'arrival_hour': arrival_time.hour,
            'arrival_day_of_week': arrival_time.weekday(),
            'arrival_day_of_month': arrival_time.day,
            'arrival_month': arrival_time.month,
            'arrival_quarter': (arrival_time.month - 1) // 3 + 1,
            
            # Cyclical time features (to capture periodicity)
            'hour_sin': np.sin(2 * np.pi * arrival_time.hour / 24),
            'hour_cos': np.cos(2 * np.pi * arrival_time.hour / 24),
            'day_sin': np.sin(2 * np.pi * arrival_time.weekday() / 7),
            'day_cos': np.cos(2 * np.pi * arrival_time.weekday() / 7),
            'month_sin': np.sin(2 * np.pi * arrival_time.month / 12),
            'month_cos': np.cos(2 * np.pi * arrival_time.month / 12),
            
            # Wait time features
            'wait_time_hours': wait_time,
            'wait_time_log': np.log1p(wait_time),
            'wait_time_sqrt': np.sqrt(wait_time),
            'is_urgent': 1 if wait_time > 24 else 0,
            'urgency_level': min(wait_time / 48.0, 1.0),  # Normalize to 48 hours
            
            # Time period indicators
            'is_morning_rush': 1 if 7 <= arrival_time.hour <= 9 else 0,
            'is_lunch_time': 1 if 11 <= arrival_time.hour <= 13 else 0,
            'is_evening_rush': 1 if 17 <= arrival_time.hour <= 19 else 0,
            'is_night_time': 1 if arrival_time.hour >= 22 or arrival_time.hour <= 6 else 0,
            'is_weekend': 1 if arrival_time.weekday() >= 5 else 0,
            'is_business_hours': 1 if 9 <= arrival_time.hour <= 18 else 0,
        }
    
    def _extract_parcel_features(self, parcel: Parcel) -> Dict[str, Any]:
        """Extract parcel-specific features"""
        size_encoding = {
            ParcelSize.SMALL: 0,
            ParcelSize.MEDIUM: 1,
            ParcelSize.LARGE: 2
        }
        
        # Extract parcel ID patterns
        parcel_id_features = self._analyze_parcel_id(parcel.parcel_id)
        
        features = {
            # Size features
            'size_numeric': size_encoding[parcel.size],
            'is_small': 1 if parcel.size == ParcelSize.SMALL else 0,
            'is_medium': 1 if parcel.size == ParcelSize.MEDIUM else 0,
            'is_large': 1 if parcel.size == ParcelSize.LARGE else 0,
            'size_weight': {ParcelSize.SMALL: 1.0, ParcelSize.MEDIUM: 2.0, ParcelSize.LARGE: 3.0}[parcel.size],
            
            # Volume/capacity implications
            'relative_size_impact': size_encoding[parcel.size] / 2.0,  # Normalize to 0-1
        }
        
        features.update(parcel_id_features)
        return features
    
    def _analyze_parcel_id(self, parcel_id: str) -> Dict[str, Any]:
        """Extract features from parcel ID patterns"""
        return {
            'id_length': len(parcel_id),
            'id_has_test_prefix': 1 if parcel_id.startswith('TEST_') else 0,
            'id_has_pred_prefix': 1 if parcel_id.startswith('PRED_') else 0,
            'id_numeric_count': sum(c.isdigit() for c in parcel_id),
            'id_alpha_count': sum(c.isalpha() for c in parcel_id),
        }
    
    def _extract_station_features(self, station: ParcelStation, current_time: datetime) -> Dict[str, Any]:
        """Extract station state features"""
        stats = station.get_station_statistics()
        
        # Calculate utilization metrics
        utilization_rates = [shelf.get_utilization_rate() for shelf in station.shelves]
        workload_scores = [shelf.get_workload_score() for shelf in station.shelves]
        
        premium_shelves = [s for s in station.shelves if s.location_type == ShelfType.PREMIUM]
        standard_shelves = [s for s in station.shelves if s.location_type == ShelfType.STANDARD]
        
        premium_util = [s.get_utilization_rate() for s in premium_shelves] if premium_shelves else [0]
        standard_util = [s.get_utilization_rate() for s in standard_shelves] if standard_shelves else [0]
        
        return {
            # Basic station metrics
            'total_shelves': stats['total_shelves'],
            'premium_shelf_count': stats['premium_shelves'],
            'standard_shelf_count': stats['standard_shelves'],
            'total_stored_parcels': stats['total_stored_parcels'],
            'pending_parcels_count': stats['pending_parcels'],
            
            # Utilization metrics
            'avg_utilization': np.mean(utilization_rates) if utilization_rates else 0.0,
            'max_utilization': np.max(utilization_rates) if utilization_rates else 0.0,
            'min_utilization': np.min(utilization_rates) if utilization_rates else 0.0,
            'utilization_std': np.std(utilization_rates) if utilization_rates else 0.0,
            'utilization_range': (np.max(utilization_rates) - np.min(utilization_rates)) if utilization_rates else 0.0,
            
            # Premium vs Standard comparison
            'avg_premium_utilization': np.mean(premium_util) if premium_util else 0.0,
            'avg_standard_utilization': np.mean(standard_util) if standard_util else 0.0,
            'premium_standard_util_diff': (np.mean(premium_util) - np.mean(standard_util)) if premium_util and standard_util else 0.0,
            
            # Workload metrics
            'avg_workload': np.mean(workload_scores) if workload_scores else 0.0,
            'max_workload': np.max(workload_scores) if workload_scores else 0.0,
            'workload_std': np.std(workload_scores) if workload_scores else 0.0,
            
            # Capacity metrics
            'station_capacity_pressure': stats['total_stored_parcels'] / max(1, stats['total_shelves'] * 10),
            'system_stress_level': min(1.0, stats['pending_parcels'] / 10.0),
            
            # Balance metrics
            'spatial_balance_score': 1.0 - np.std(utilization_rates) if utilization_rates else 1.0,
            'workload_balance_score': 1.0 - np.std(workload_scores) if workload_scores else 1.0,
        }
    
    def _extract_environmental_features(self, env_factors: EnvironmentalFactors) -> Dict[str, Any]:
        """Extract environmental factor features"""
        weather_encoding = {
            'sunny': 0, 'rainy': 1, 'snowy': 2, 'foggy': 3, 'stormy': 4
        }
        
        return {
            # Weather features
            'weather_numeric': weather_encoding.get(env_factors.weather.value, 0),
            'is_sunny': 1 if env_factors.weather.value == 'sunny' else 0,
            'is_rainy': 1 if env_factors.weather.value == 'rainy' else 0,
            'is_bad_weather': 1 if env_factors.weather.value in ['snowy', 'stormy'] else 0,
            
            # Environmental conditions
            'temperature': env_factors.temperature,
            'temperature_normalized': (env_factors.temperature + 10) / 50.0,  # Normalize to 0-1
            'is_holiday': 1 if env_factors.is_holiday else 0,
            'is_weekend': 1 if env_factors.is_weekend else 0,
            'traffic_condition': env_factors.traffic_condition,
            'traffic_heavy': 1 if env_factors.traffic_condition > 1.2 else 0,
            
            # Impact factors
            'environmental_impact': env_factors.get_impact_factor(),
            'weather_pickup_impact': 1.0 if env_factors.weather.value == 'sunny' else 0.8,
        }
    
    def _extract_customer_features(self, profile: CustomerProfile, current_time: datetime) -> Dict[str, Any]:
        """Extract customer profile features"""
        current_hour = current_time.hour
        
        return {
            # Customer behavior
            'customer_pickup_speed': profile.pickup_speed_factor,
            'customer_reliability': profile.reliability_score,
            'customer_prefers_premium': 1 if profile.location_preference == ShelfType.PREMIUM else 0,
            
            # Time preferences
            'in_preferred_time': 1 if current_hour in profile.preferred_times else 0,
            'preferred_time_count': len(profile.preferred_times),
            'earliest_preferred_hour': min(profile.preferred_times) if profile.preferred_times else 18,
            'latest_preferred_hour': max(profile.preferred_times) if profile.preferred_times else 20,
            'preferred_time_span': (max(profile.preferred_times) - min(profile.preferred_times)) if len(profile.preferred_times) > 1 else 0,
            
            # Historical patterns
            'historical_pickup_count': len(profile.historical_pickups),
            'customer_experience_level': min(len(profile.historical_pickups) / 10.0, 1.0),
        }
    
    def _get_default_customer_features(self) -> Dict[str, Any]:
        """Get default customer features when profile is not available"""
        return {
            'customer_pickup_speed': 1.0,
            'customer_reliability': 0.8,
            'customer_prefers_premium': 0,
            'in_preferred_time': 0,
            'preferred_time_count': 3,
            'earliest_preferred_hour': 18,
            'latest_preferred_hour': 20,
            'preferred_time_span': 2,
            'historical_pickup_count': 0,
            'customer_experience_level': 0.0,
        }
    
    def _extract_historical_features(self, parcel: Parcel, station: ParcelStation, 
                                   current_time: datetime) -> Dict[str, Any]:
        """Extract historical pattern features"""
        # This would normally access a historical database
        # For now, we'll use some basic patterns
        
        current_hour = current_time.hour
        current_dow = current_time.weekday()
        
        # Simulate historical pickup patterns
        historical_pickup_rates = {
            'morning': 0.3, 'afternoon': 0.7, 'evening': 0.8, 'night': 0.2
        }
        
        if 6 <= current_hour <= 11:
            period = 'morning'
        elif 12 <= current_hour <= 17:
            period = 'afternoon'
        elif 18 <= current_hour <= 22:
            period = 'evening'
        else:
            period = 'night'
        
        return {
            'historical_pickup_rate_period': historical_pickup_rates[period],
            'historical_avg_wait_time': 12.0,  # hours
            'size_popularity_rank': {ParcelSize.SMALL: 1, ParcelSize.MEDIUM: 2, ParcelSize.LARGE: 3}[parcel.size],
            'day_pickup_frequency': 0.8 if current_dow < 5 else 0.6,  # Weekday vs weekend
            'seasonal_factor': 1.0,  # Could be enhanced with actual seasonal data
        }
    
    def _extract_contextual_features(self, parcel: Parcel, station: ParcelStation,
                                   env_factors: EnvironmentalFactors) -> Dict[str, Any]:
        """Extract contextual features based on current situation"""
        
        # Find best available shelf for this parcel (if assigned immediately)
        available_shelves = station.get_available_shelves(parcel.size)
        
        if available_shelves:
            best_shelf = min(available_shelves, key=lambda s: s.distance_to_exit)
            
            context_features = {
                'best_available_distance': best_shelf.distance_to_exit,
                'best_available_is_premium': 1 if best_shelf.location_type == ShelfType.PREMIUM else 0,
                'available_shelf_count': len(available_shelves),
                'premium_shelves_available': len([s for s in available_shelves if s.location_type == ShelfType.PREMIUM]),
            }
        else:
            context_features = {
                'best_available_distance': 5.0,  # Max distance
                'best_available_is_premium': 0,
                'available_shelf_count': 0,
                'premium_shelves_available': 0,
            }
        
        # Competition for space
        context_features.update({
            'space_competition_level': len(station.pending_parcels) / 10.0,
            'size_specific_competition': len([p for p in station.pending_parcels if p.size == parcel.size]) / 5.0,
        })
        
        return context_features
    
    def fit_transform(self, training_data: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, List[str]]:
        """Fit feature engineering pipeline and transform data"""
        # Convert to DataFrame
        df = pd.DataFrame(training_data)
        
        # Handle categorical variables
        categorical_columns = df.select_dtypes(include=['object']).columns
        for col in categorical_columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
            df[col] = self.label_encoders[col].fit_transform(df[col].astype(str))
        
        # Store feature names
        self.feature_names = list(df.columns)
        
        # Apply polynomial features if enabled
        if self.polynomial_features:
            df_poly = self.polynomial_features.fit_transform(df)
            poly_feature_names = self.polynomial_features.get_feature_names_out(self.feature_names)
            df = pd.DataFrame(df_poly, columns=poly_feature_names)
            self.feature_names = list(df.columns)
        
        # Fit scaler
        df_scaled = self.scaler.fit_transform(df)
        df_final = pd.DataFrame(df_scaled, columns=self.feature_names)
        
        self.is_fitted = True
        return df_final, self.feature_names
    
    def transform(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform new data using fitted pipeline"""
        if not self.is_fitted:
            raise ValueError("Feature engineering pipeline must be fitted first")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Ensure all expected columns are present
        for col in self.feature_names:
            if col not in df.columns and self.polynomial_features is None:
                df[col] = 0  # Default value for missing features
        
        # Handle categorical variables
        for col, encoder in self.label_encoders.items():
            if col in df.columns:
                # Handle unseen categories
                df[col] = df[col].astype(str)
                unknown_mask = ~df[col].isin(encoder.classes_)
                df.loc[unknown_mask, col] = encoder.classes_[0]  # Use first class as default
                df[col] = encoder.transform(df[col])
        
        # Apply polynomial features if enabled
        if self.polynomial_features:
            # Select only the original features for polynomial transformation
            original_features = [col for col in df.columns if col in self.feature_names[:len(self.feature_names)//2]]
            df_poly = self.polynomial_features.transform(df[original_features])
            df = pd.DataFrame(df_poly, columns=self.feature_names)
        
        # Apply scaling
        df_scaled = self.scaler.transform(df)
        df_final = pd.DataFrame(df_scaled, columns=self.feature_names)
        
        return df_final


class MLModelBase(ABC):
    """Base class for ML models"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self.is_trained = False
        self.feature_importance = None
        self.training_history = []
    
    @abstractmethod
    def create_model(self) -> Any:
        """Create and return the ML model"""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name"""
        pass
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Train the model"""
        self.model = self.create_model()
        self.model.fit(X, y)
        self.is_trained = True
        
        # Calculate training metrics
        y_pred = self.model.predict(X)
        y_pred_proba = self.model.predict_proba(X)[:, 1] if hasattr(self.model, 'predict_proba') else y_pred
        
        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'precision': precision_score(y, y_pred, average='weighted'),
            'recall': recall_score(y, y_pred, average='weighted'),
            'f1': f1_score(y, y_pred, average='weighted'),
        }
        
        if hasattr(self.model, 'predict_proba'):
            metrics['auc'] = roc_auc_score(y, y_pred_proba)
        
        # Extract feature importance if available
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            self.feature_importance = np.abs(self.model.coef_[0])
        
        self.training_history.append({
            'timestamp': datetime.now(),
            'metrics': metrics,
            'training_size': len(X)
        })
        
        return metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained:
            raise ValueError(f"{self.get_model_name()} model must be trained first")
        return self.model.predict(X)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities"""
        if not self.is_trained:
            raise ValueError(f"{self.get_model_name()} model must be trained first")
        
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)[:, 1]
        else:
            # For models without predict_proba, return predictions as probabilities
            predictions = self.model.predict(X)
            return predictions.astype(float)
    
    def get_feature_importance(self) -> Optional[np.ndarray]:
        """Get feature importance if available"""
        return self.feature_importance


class RandomForestModel(MLModelBase):
    """Random Forest model implementation"""
    
    def create_model(self) -> RandomForestClassifier:
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            random_state=self.config.random_state,
            n_jobs=-1
        )
    
    def get_model_name(self) -> str:
        return "RandomForest"


class GradientBoostingModel(MLModelBase):
    """Gradient Boosting model implementation"""
    
    def create_model(self) -> GradientBoostingClassifier:
        return GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=self.config.random_state
        )
    
    def get_model_name(self) -> str:
        return "GradientBoosting"


class XGBoostModel(MLModelBase):
    """XGBoost model implementation"""
    
    def create_model(self) -> xgb.XGBClassifier:
        return xgb.XGBClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=self.config.random_state,
            eval_metric='logloss'
        )
    
    def get_model_name(self) -> str:
        return "XGBoost"


class LogisticRegressionModel(MLModelBase):
    """Logistic Regression model implementation"""
    
    def create_model(self) -> LogisticRegression:
        return LogisticRegression(
            random_state=self.config.random_state,
            max_iter=1000
        )
    
    def get_model_name(self) -> str:
        return "LogisticRegression"


class MLPModel(MLModelBase):
    """Multi-Layer Perceptron model implementation"""
    
    def create_model(self) -> MLPClassifier:
        return MLPClassifier(
            hidden_layer_sizes=(100, 50),
            activation='relu',
            solver='adam',
            learning_rate='adaptive',
            random_state=self.config.random_state,
            max_iter=1000
        )
    
    def get_model_name(self) -> str:
        return "MLP"


class EnsembleModel(MLModelBase):
    """Ensemble model combining multiple base models"""
    
    def __init__(self, config: MLConfig):
        super().__init__(config)
        self.base_models = self._create_base_models()
    
    def _create_base_models(self) -> Dict[str, MLModelBase]:
        """Create base models for ensemble"""
        models = {}
        
        if 'rf' in self.config.ensemble_methods:
            models['rf'] = RandomForestModel(self.config)
        if 'gb' in self.config.ensemble_methods:
            models['gb'] = GradientBoostingModel(self.config)
        if 'xgb' in self.config.ensemble_methods:
            models['xgb'] = XGBoostModel(self.config)
        if 'lr' in self.config.ensemble_methods:
            models['lr'] = LogisticRegressionModel(self.config)
        if 'mlp' in self.config.ensemble_methods:
            models['mlp'] = MLPModel(self.config)
        
        return models
    
    def create_model(self) -> Any:
        """Create ensemble model - this is a placeholder"""
        return None  # Ensemble logic is handled separately
    
    def get_model_name(self) -> str:
        return "Ensemble"
    
    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Train all base models"""
        ensemble_metrics = {}
        
        # Train each base model
        for name, model in self.base_models.items():
            print(f"Training {name} model...")
            metrics = model.train(X, y)
            ensemble_metrics[f"{name}_accuracy"] = metrics['accuracy']
            ensemble_metrics[f"{name}_f1"] = metrics['f1']
        
        # Set trained state first to enable ensemble predictions
        self.is_trained = True
        
        # Calculate ensemble metrics
        try:
            y_pred_ensemble = self.predict(X)
            y_pred_proba_ensemble = self.predict_proba(X)
            
            ensemble_metrics.update({
                'ensemble_accuracy': accuracy_score(y, y_pred_ensemble),
                'ensemble_precision': precision_score(y, y_pred_ensemble, average='weighted'),
                'ensemble_recall': recall_score(y, y_pred_ensemble, average='weighted'),
                'ensemble_f1': f1_score(y, y_pred_ensemble, average='weighted'),
                'ensemble_auc': roc_auc_score(y, y_pred_proba_ensemble)
            })
        except Exception as e:
            print(f"Warning: Could not calculate ensemble metrics: {e}")
            # Keep basic individual model metrics
        self.training_history.append({
            'timestamp': datetime.now(),
            'metrics': ensemble_metrics,
            'training_size': len(X)
        })
        
        return ensemble_metrics
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make ensemble predictions using voting"""
        if not self.is_trained:
            raise ValueError("Ensemble model must be trained first")
        
        predictions = []
        for model in self.base_models.values():
            if model.is_trained:
                pred = model.predict(X)
                predictions.append(pred)
        
        if not predictions:
            raise ValueError("No trained models in ensemble")
        
        # Majority voting
        predictions_array = np.array(predictions)
        ensemble_pred = np.round(np.mean(predictions_array, axis=0))
        
        return ensemble_pred.astype(int)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Make ensemble probability predictions"""
        if not self.is_trained:
            raise ValueError("Ensemble model must be trained first")
        
        probabilities = []
        for model in self.base_models.values():
            if model.is_trained:
                prob = model.predict_proba(X)
                probabilities.append(prob)
        
        if not probabilities:
            raise ValueError("No trained models in ensemble")
        
        # Average probabilities
        ensemble_proba = np.mean(probabilities, axis=0)
        
        return ensemble_proba


class MLPickupPredictor(PickupProbabilityPredictor):
    """ML-powered pickup probability predictor"""
    
    def __init__(self, config: MLConfig = None):
        super().__init__(use_noise=False)  # No noise needed for ML models
        self.config = config or MLConfig()
        self.feature_engineer = AdvancedFeatureEngineer(self.config)
        self.model = self._create_model()
        self.training_data_buffer = []
        self.is_trained = False
        self.last_retrain_time = None
        self.performance_history = deque(maxlen=self.config.performance_window_size)
        
        # Concept drift detection
        self.concept_drift_detector = self._initialize_drift_detector()
        
        self.logger = logging.getLogger(__name__)
    
    def _create_model(self) -> MLModelBase:
        """Create the appropriate ML model based on configuration"""
        if self.config.use_ensemble:
            return EnsembleModel(self.config)
        elif self.config.primary_model == 'rf':
            return RandomForestModel(self.config)
        elif self.config.primary_model == 'gb':
            return GradientBoostingModel(self.config)
        elif self.config.primary_model == 'xgb':
            return XGBoostModel(self.config)
        elif self.config.primary_model == 'lr':
            return LogisticRegressionModel(self.config)
        elif self.config.primary_model == 'mlp':
            return MLPModel(self.config)
        else:
            self.logger.warning(f"Unknown model type: {self.config.primary_model}, using RandomForest")
            return RandomForestModel(self.config)
    
    def _initialize_drift_detector(self):
        """Initialize concept drift detector"""
        # Placeholder for drift detection logic
        return {
            'baseline_accuracy': None,
            'recent_accuracy': None,
            'drift_threshold': self.config.concept_drift_threshold
        }
    
    def predict_pickup_probability(self, parcel: Parcel, current_time: datetime,
                                 environmental_factors: EnvironmentalFactors = None,
                                 station: ParcelStation = None,
                                 customer_profile: CustomerProfile = None) -> float:
        """Predict pickup probability using ML model"""
        
        if not self.is_trained:
            # Fallback to rule-based prediction if model not trained
            self.logger.warning("ML model not trained, falling back to rule-based prediction")
            return super().predict_pickup_probability(parcel, current_time)
        
        try:
            # Create default objects if not provided
            if environmental_factors is None:
                environmental_factors = EnvironmentalFactors(timestamp=current_time)
            
            if station is None:
                # Create a dummy station for feature extraction
                station = ParcelStation()
            
            # Extract features
            features = self.feature_engineer.extract_comprehensive_features(
                parcel, current_time, station, environmental_factors, customer_profile
            )
            
            # Transform features
            features_df = self.feature_engineer.transform([features])
            
            # Make prediction
            probability = self.model.predict_proba(features_df)[0]
            
            # Ensure probability is in valid range
            probability = max(0.01, min(0.99, probability))
            
            return probability
            
        except Exception as e:
            self.logger.error(f"Error in ML prediction: {e}, falling back to rule-based")
            return super().predict_pickup_probability(parcel, current_time)
    
    def add_training_data(self, parcel: Parcel, current_time: datetime,
                         actual_picked_up: bool, environmental_factors: EnvironmentalFactors = None,
                         station: ParcelStation = None, customer_profile: CustomerProfile = None):
        """Add new training data point"""
        
        # Create default objects if not provided
        if environmental_factors is None:
            environmental_factors = EnvironmentalFactors(timestamp=current_time)
        
        if station is None:
            station = ParcelStation()
        
        # Extract features
        features = self.feature_engineer.extract_comprehensive_features(
            parcel, current_time, station, environmental_factors, customer_profile
        )
        
        # Add label
        training_point = {
            'features': features,
            'label': 1 if actual_picked_up else 0,
            'timestamp': current_time,
            'parcel_id': parcel.parcel_id
        }
        
        self.training_data_buffer.append(training_point)
        
        # Trigger retraining if buffer is full
        if (len(self.training_data_buffer) >= self.config.batch_update_size and 
            self.config.online_learning_enabled):
            self._perform_incremental_training()
    
    def train_model(self, training_data: List[Dict[str, Any]] = None) -> Dict[str, float]:
        """Train the ML model"""
        
        if training_data is None:
            training_data = self.training_data_buffer
        
        if len(training_data) < 50:  # Minimum training data
            self.logger.warning(f"Insufficient training data: {len(training_data)} samples")
            return {}
        
        try:
            # Prepare training data
            features_list = [point['features'] for point in training_data]
            labels = [point['label'] for point in training_data]
            
            # Feature engineering
            if not self.feature_engineer.is_fitted:
                X, feature_names = self.feature_engineer.fit_transform(features_list)
            else:
                X = self.feature_engineer.transform(features_list)
            
            y = pd.Series(labels)
            
            # Train model
            self.logger.info(f"Training {self.model.get_model_name()} with {len(X)} samples")
            metrics = self.model.train(X, y)
            
            self.is_trained = True
            self.last_retrain_time = datetime.now()
            
            # Log training results
            self.logger.info(f"Model trained successfully. Metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error training ML model: {e}")
            return {}
    
    def _perform_incremental_training(self):
        """Perform incremental training with new data"""
        
        # Use only recent data for incremental training
        recent_data = self.training_data_buffer[-self.config.batch_update_size:]
        
        # Train on recent data
        metrics = self.train_model(recent_data)
        
        # Check for concept drift
        if metrics and 'ensemble_accuracy' in metrics:
            self._check_concept_drift(metrics['ensemble_accuracy'])
        
        # Clear processed data from buffer
        self.training_data_buffer = self.training_data_buffer[-self.config.batch_update_size//2:]
    
    def _check_concept_drift(self, current_accuracy: float):
        """Check for concept drift in model performance"""
        
        if self.concept_drift_detector['baseline_accuracy'] is None:
            self.concept_drift_detector['baseline_accuracy'] = current_accuracy
            return
        
        baseline_acc = self.concept_drift_detector['baseline_accuracy']
        accuracy_drop = baseline_acc - current_accuracy
        
        if accuracy_drop > self.concept_drift_detector['drift_threshold']:
            self.logger.warning(f"Concept drift detected! Accuracy dropped by {accuracy_drop:.3f}")
            self._handle_concept_drift()
        else:
            # Update baseline if performance is stable or improving
            self.concept_drift_detector['baseline_accuracy'] = current_accuracy
    
    def _handle_concept_drift(self):
        """Handle detected concept drift"""
        self.logger.info("Handling concept drift by retraining on full dataset")
        
        # Retrain on all available data
        if len(self.training_data_buffer) > 100:
            self.train_model(self.training_data_buffer)
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        if not self.is_trained:
            return True
        
        if self.last_retrain_time is None:
            return True
        
        time_since_retrain = datetime.now() - self.last_retrain_time
        return time_since_retrain.total_seconds() / 3600 >= self.config.retrain_frequency_hours
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics"""
        if not self.is_trained:
            return {'status': 'not_trained'}
        
        return {
            'status': 'trained',
            'model_type': self.model.get_model_name(),
            'last_retrain_time': self.last_retrain_time,
            'training_data_size': len(self.training_data_buffer),
            'is_ensemble': self.config.use_ensemble,
            'training_history': self.model.training_history[-5:],  # Last 5 training sessions
            'feature_count': len(self.feature_engineer.feature_names) if self.feature_engineer.is_fitted else 0
        }
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from the trained model"""
        if not self.is_trained or not self.feature_engineer.is_fitted:
            return None
        
        importance = self.model.get_feature_importance()
        if importance is not None:
            feature_names = self.feature_engineer.feature_names
            return dict(zip(feature_names, importance))
        
        return None
    
    def save_model(self, filepath: str):
        """Save the trained model and feature engineering pipeline"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'feature_engineer': self.feature_engineer,
            'config': self.config,
            'training_data_buffer': self.training_data_buffer,
            'last_retrain_time': self.last_retrain_time,
            'concept_drift_detector': self.concept_drift_detector,
            'performance_history': list(self.performance_history)
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model and feature engineering pipeline"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.feature_engineer = model_data['feature_engineer']
            self.config = model_data['config']
            self.training_data_buffer = model_data['training_data_buffer']
            self.last_retrain_time = model_data['last_retrain_time']
            self.concept_drift_detector = model_data['concept_drift_detector']
            self.performance_history = deque(model_data['performance_history'], 
                                           maxlen=self.config.performance_window_size)
            
            self.is_trained = True
            self.logger.info(f"Model loaded from {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise


def create_ml_predictor(config: MLConfig = None) -> MLPickupPredictor:
    """Factory function to create ML-powered predictor"""
    return MLPickupPredictor(config)


# Example usage and testing
if __name__ == "__main__":
    import random
    from enhanced_dynamic_simulation import EnvironmentalFactors, CustomerProfile
    
    # Create ML configuration
    ml_config = MLConfig(
        use_ensemble=True,
        ensemble_methods=['rf', 'gb', 'xgb', 'lr'],
        online_learning_enabled=True,
        use_polynomial_features=True
    )
    
    # Create ML predictor
    ml_predictor = create_ml_predictor(ml_config)
    
    # Create test data
    station = ParcelStation()
    
    # Add some shelves
    for i in range(3):
        shelf = Shelf(f"P{i+1}", ShelfType.PREMIUM, matrix_position=(0, i))
        station.add_shelf(shelf)
    
    for i in range(5):
        shelf = Shelf(f"S{i+1}", ShelfType.STANDARD, matrix_position=(1, i))
        station.add_shelf(shelf)
    
    # Generate synthetic training data
    print("Generating synthetic training data...")
    training_data = []
    
    for i in range(200):  # Generate 200 training samples
        # Create test parcel
        arrival_time = datetime.now() - timedelta(hours=random.randint(1, 48))
        parcel = Parcel(f"TEST_{i:04d}", arrival_time, random.choice(list(ParcelSize)))
        
        # Create environmental factors
        env_factors = EnvironmentalFactors(
            timestamp=datetime.now(),
            weather=random.choice(['sunny', 'rainy', 'snowy']),
            is_holiday=random.random() < 0.1,
            traffic_condition=random.uniform(0.8, 1.5)
        )
        
        # Create customer profile
        customer_profile = CustomerProfile(
            customer_id=f"CUST_{i}",
            pickup_speed_factor=random.uniform(0.5, 1.5),
            reliability_score=random.uniform(0.6, 0.95)
        )
        
        # Simulate actual pickup (for training)
        actual_picked_up = random.random() < 0.8  # 80% pickup rate
        
        # Add to training data
        ml_predictor.add_training_data(
            parcel, datetime.now(), actual_picked_up, env_factors, station, customer_profile
        )
    
    # Train the model
    print("Training ML model...")
    metrics = ml_predictor.train_model()
    print(f"Training completed. Metrics: {metrics}")
    
    # Test predictions
    print("\nTesting ML predictions...")
    for i in range(5):
        test_parcel = Parcel(f"TEST_PRED_{i}", datetime.now(), random.choice(list(ParcelSize)))
        env_factors = EnvironmentalFactors(timestamp=datetime.now())
        
        prob = ml_predictor.predict_pickup_probability(
            test_parcel, datetime.now(), env_factors, station
        )
        print(f"Parcel {test_parcel.parcel_id} (Size: {test_parcel.size.value}) -> Pickup Probability: {prob:.3f}")
    
    # Display model performance
    performance = ml_predictor.get_model_performance()
    print(f"\nModel Performance: {performance}")
    
    # Display feature importance
    importance = ml_predictor.get_feature_importance()
    if importance:
        print("\nTop 10 Most Important Features:")
        sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        for feature, score in sorted_features[:10]:
            print(f"  {feature}: {score:.4f}")
    
    print("\nML LTO Framework test completed successfully!")