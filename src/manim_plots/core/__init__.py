"""Array types and warnings shared by the numeric core."""

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.intp]


class ManimPlotsWarning(UserWarning):
    """Report a recoverable condition encountered while using a plot."""
