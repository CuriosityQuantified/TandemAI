# Descriptive Statistics Analysis

## Dataset Description

**Dataset**: 10, 20, 30, 40, 50
**Sample Size (n)**: 5
**Data Type**: Numerical (continuous)
**Range**: 10 to 50

---

## Mean Calculation

### Formula
$$\bar{x} = \frac{\sum_{i=1}^{n} x_i}{n}$$

### Step-by-Step Calculation

| Step | Calculation |
|------|-------------|
| 1. Sum all values | 10 + 20 + 30 + 40 + 50 = 150 |
| 2. Count observations | n = 5 |
| 3. Divide sum by count | 150 ÷ 5 = 30 |

**Mean (Average) = 30**

---

## Standard Deviation Calculation

### Sample Standard Deviation (s)

Used when data represents a sample from a larger population.

**Formula:**
$$s = \sqrt{\frac{\sum_{i=1}^{n} (x_i - \bar{x})^2}{n-1}}$$

**Step-by-Step Calculation:**

| Value (x) | Deviation (x - x̄) | Squared Deviation (x - x̄)² |
|-----------|------------------|---------------------------|
| 10 | 10 - 30 = -20 | (-20)² = 400 |
| 20 | 20 - 30 = -10 | (-10)² = 100 |
| 30 | 30 - 30 = 0 | (0)² = 0 |
| 40 | 40 - 30 = 10 | (10)² = 100 |
| 50 | 50 - 30 = 20 | (20)² = 400 |

**Calculations:**
1. Sum of squared deviations: 400 + 100 + 0 + 100 + 400 = **1000**
2. Degrees of freedom: n - 1 = 5 - 1 = **4**
3. Variance (sample): 1000 ÷ 4 = **250**
4. Standard deviation (sample): √250 = **15.81**

**Sample Standard Deviation (s) = 15.81**

---

### Population Standard Deviation (σ)

Used when data represents the entire population of interest.

**Formula:**
$$\sigma = \sqrt{\frac{\sum_{i=1}^{n} (x_i - \bar{x})^2}{n}}$$

**Calculations:**
1. Sum of squared deviations: **1000** (same as above)
2. Population size: n = **5**
3. Variance (population): 1000 ÷ 5 = **200**
4. Standard deviation (population): √200 = **14.14**

**Population Standard Deviation (σ) = 14.14**

---

## Summary Statistics Table

| Statistic | Value |
|-----------|-------|
| Count | 5 |
| Mean | 30.00 |
| Median | 30.00 |
| Mode | None (all values unique) |
| Minimum | 10 |
| Maximum | 50 |
| Range | 40 |
| Sample Variance (s²) | 250.00 |
| Population Variance (σ²) | 200.00 |
| Sample Std Dev (s) | 15.81 |
| Population Std Dev (σ) | 14.14 |
| Coefficient of Variation (CV) | 52.7% |

---

## Interpretation of Findings

### Mean (30)
The average value of the dataset is **30**, which is also the median. This indicates:
- The data is symmetrically distributed around the center point
- All values are evenly spaced from the mean
- The central tendency is well-represented by the mean

### Standard Deviation

**Sample Standard Deviation (s = 15.81):**
- This is the most appropriate measure if these 5 values represent a sample from a larger population
- On average, values deviate from the mean by approximately **±15.81 units**
- Approximately 68% of values fall within the range [30 - 15.81, 30 + 15.81] = [14.19, 45.81]
- All actual values (10, 20, 30, 40, 50) fall within this range

**Population Standard Deviation (σ = 14.14):**
- Use this if these 5 values represent the complete dataset of interest
- Slightly lower than sample standard deviation due to different denominator (n vs n-1)

### Coefficient of Variation (52.7%)
- Relative variability: Standard deviation is 52.7% of the mean
- Indicates moderate to high relative variability
- Useful for comparing variability across datasets with different scales

---

## Distribution Characteristics

### Symmetry
- **Perfect Symmetry**: The dataset is perfectly symmetric around the mean
- Values equidistant from center: (10, 50), (20, 40), with 30 at center
- Mean = Median indicates symmetric distribution

### Spread
- **Uniform Distribution**: Values are evenly spaced (spacing of 10 units)
- **No Outliers**: All values follow the same pattern; no anomalies detected
- **Moderate Variability**: CV of 52.7% indicates reasonable spread relative to mean

### Shape
- **Linear Progression**: Values increase at constant rate
- **No Skewness**: Distribution is perfectly symmetric (skewness = 0)
- **Platykurtic**: Uniform distribution has negative excess kurtosis (-1.2)

---

## Additional Statistical Insights

### 1. Data Quality
✓ **No missing values**: All 5 data points provided
✓ **No outliers**: All values follow consistent pattern
✓ **Complete dataset**: n = 5 as specified

### 2. Confidence Intervals (95%)

**For the Mean (assuming normal distribution):**
- Standard Error: SE = s/√n = 15.81/√5 = 7.07
- t-critical (df=4, α=0.05): t = 2.776
- Margin of Error: 2.776 × 7.07 = 19.63
- **95% CI: [10.37, 49.63]**

This means if we repeated sampling, 95% of sample means would fall within this range.

### 3. Variance Analysis
- **Sample Variance**: 250.00 (larger denominator: n-1=4)
- **Population Variance**: 200.00 (smaller denominator: n=5)
- **Ratio**: Sample variance is 1.25× population variance
- The difference decreases as sample size increases

### 4. Standardized Scores (Z-scores)

| Value | Z-score |
|-------|---------|
| 10 | -1.265 |
| 20 | -0.633 |
| 30 | 0.000 |
| 40 | 0.633 |
| 50 | 1.265 |

All z-scores fall within ±2σ, confirming no statistical outliers.

---

## Recommendations

1. **Use Sample Standard Deviation (s = 15.81)** if these 5 values are a sample from a larger population
2. **Use Population Standard Deviation (σ = 14.14)** only if these 5 values represent your complete dataset of interest
3. **Report both Mean and Standard Deviation** when communicating results: **Mean ± SD = 30 ± 15.81**
4. **Consider the context** of your data when interpreting the 52.7% coefficient of variation

---

## Conclusion

The dataset exhibits:
- **Central Tendency**: Well-defined mean of 30
- **Variability**: Moderate spread (SD ≈ 15.81)
- **Distribution**: Perfect symmetry with uniform spacing
- **Quality**: No missing values or outliers
- **Reliability**: Stable estimates suitable for further analysis

