"""
Compatibility wrapper exposing LSTMForecastModel in `app.lstm` namespace.
This adapter reuses the concrete implementation in `app.models.lstm_model.LSTMModel`.
It ensures existing imports `from app.lstm.lstm_model import LSTMForecastModel`
continue to work without modifying callers.
"""
from typing import Optional, Tuple

from app.models.lstm_model import LSTMModel


class LSTMForecastModel:
    """Adapter compatible with existing code that expects an object
    with a `.model` attribute (Keras model) and similar training/predict behavior.

    Parameters
    ----------
    input_shape: optional tuple
        If provided, the underlying Keras model is built immediately via
        the protected `_build_model` helper of `LSTMModel`.
    """

    def __init__(self, input_shape: Optional[Tuple[int, int]] = None, **kwargs):
        self._impl = LSTMModel(**kwargs)
        # If caller expects a .model attribute (Keras model), build it now.
        if input_shape is not None:
            # Use the existing builder on the implementation to keep consistency
            self._impl.model = self._impl._build_model(input_shape)

    @property
    def model(self):
        return self._impl.model

    @model.setter
    def model(self, value):
        self._impl.model = value

    # Convenience pass-throughs to mimic previous API
    def train(self, *args, **kwargs):
        return self._impl.train(*args, **kwargs)

    def predict(self, *args, **kwargs):
        # prefer direct model.predict if available
        if self.model is not None:
            return self.model.predict(*args, **kwargs)
        return self._impl.predict(*args, **kwargs)

    # Expose underlying implementation if needed
    @property
    def impl(self):
        return self._impl
