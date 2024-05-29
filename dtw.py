import numpy as np
import piheaan as heaan
from piheaan.math import sort
from piheaan.math import approx
import math
import numpy as np
import pandas as pd
import os

# Calculate the DTW distance between two sequences
def dtw(s, t):
    n, m = len(s), len(t)
    dtw_matrix = [[float('inf')] * (m + 1) for _ in range(2)]

    dtw_matrix[0][0] = 0

    for i in range(1, n + 1):
        dtw_matrix[1][0] = float('inf')
        for j in range(1, m + 1):
            cost = abs(s[i-1] - t[j-1])
            dtw_matrix[1][j] = cost + min(dtw_matrix[1][j-1],   # Left
                                          dtw_matrix[0][j],     # Up
                                          dtw_matrix[0][j-1])  # Diagonal
        dtw_matrix[0] = dtw_matrix[1][:]
    
    return dtw_matrix[1][m]

# Example usage
s = [1, 3, 4, 9]
t = [2, 5, 7, 9]
print("DTW distance:", dtw(s, t))
