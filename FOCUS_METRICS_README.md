# Focus and Performance Metrics

This project writes one summary row per completed test into the Google Sheets `Data` tab.

The first 12 columns are the original session summary fields. The added columns extend that row with sport-science style indicators describing focus endurance, vigilance drift, and speed-accuracy regulation across the task.

## Input Data Used

Each metric is computed from the per-trial fields already captured by the app:

- `Trial`
- `Trial Time`
- `Response Time`
- `Success` (`1` for correct, `0` for incorrect)

## Session Segmentation

Third-based metrics use the same time-on-task segmentation already used by `IES1`, `IES2`, and `IES3`:

- `1st Third`: trials whose `Trial Time` falls in the first third of task duration
- `2nd Third`: trials whose `Trial Time` falls in the middle third
- `3rd Third`: trials whose `Trial Time` falls in the last third

This keeps the new indicators aligned with the existing focus drift and stability calculations.

## Existing Metrics

### Overall IES Score

`IES = median correct RT / accuracy`

- Correct RT uses only successful trials
- Accuracy is `successful trials / total trials`
- Overall IES is the geometric mean of `IES1`, `IES2`, and `IES3`

### IES1, IES2, IES3

The same IES formula applied separately to the first, second, and third time segments.

### Focus Drift

`Focus Drift = IES1 - IES3`

- Positive values mean the athlete became more efficient by the end
- Negative values mean efficiency worsened over time

### Focus Stability

This is based on the average absolute deviation of `IES1`, `IES2`, and `IES3` around their mean:

`Focus Stability = 100 * (1 - average deviation / mean IES)`

The value is clamped between `0` and `100`.

## Added Metrics

### Overall Accuracy (%)

`100 * successful trials / total trials`

### Overall Median RT (s)

Median response time across all trials with a valid response time.

### Overall RT CV

`standard deviation of RT / mean RT`

This is the coefficient of variation and reflects response-time consistency.

### Overall Lapse Rate (%)

Percentage of responses slower than the session lapse threshold:

`lapse threshold = session median RT + 2 * session RT standard deviation`

`Overall Lapse Rate = 100 * lapses / total valid RT trials`

### Accuracy 1st Third (%), Accuracy 2nd Third (%), Accuracy 3rd Third (%)

Accuracy computed separately in each time segment:

`100 * successful trials in segment / total trials in segment`

### Median RT 1st Third (s), Median RT 2nd Third (s), Median RT 3rd Third (s)

Median response time computed separately in each time segment.

### RT CV 1st Third, RT CV 2nd Third, RT CV 3rd Third

Coefficient of variation of response time computed separately in each time segment.

### Lapse Rate 1st Third (%), Lapse Rate 2nd Third (%), Lapse Rate 3rd Third (%)

Percentage of trials in each segment with RT above the session lapse threshold.

Using one session-wide threshold makes the thirds directly comparable.

### RT Decrement (%)

`100 * (Median RT 3rd Third - Median RT 1st Third) / Median RT 1st Third`

- Positive values mean the athlete became slower
- Negative values mean the athlete became faster

### Accuracy Decrement (%)

`100 * (Accuracy 3rd Third - Accuracy 1st Third) / Accuracy 1st Third`

- Negative values mean accuracy dropped
- Positive values mean accuracy improved

### IES Decrement (%)

`100 * (IES3 - IES1) / IES1`

- Positive values mean efficiency worsened
- Negative values mean efficiency improved

### RT Slope

Linear regression slope of `Response Time` over ordered trial number.

- Positive slope: slowing over time
- Negative slope: speeding up over time

### Success Slope

Linear regression slope of `Success` (`1/0`) over ordered trial number.

- Positive slope: improving success probability
- Negative slope: declining success probability

### IES Slope

Linear regression slope of the valid block IES values across the three time segments.

- Positive slope: efficiency getting worse across the task
- Negative slope: efficiency improving

### Error Rate Slope

Linear regression slope of `Error = 1 - Success` over ordered trial number.

- Positive slope: errors becoming more frequent
- Negative slope: errors becoming less frequent

### Post-Error RT Delta (s)

`mean RT after an error - mean RT after a correct response`

- Positive values suggest post-error slowing
- Negative values suggest faster responses after errors

### Post-Error Accuracy Delta (pp)

`100 * (mean success after an error - mean success after a correct response)`

The unit is percentage points (`pp`), not relative percent.

### RT-Success Correlation

Pearson correlation between `Response Time` and `Success`.

- Positive values mean slower responses tend to be more accurate
- Negative values mean slower responses tend to be less accurate
- Values near `0` mean little linear speed-accuracy coupling

## Blank Values

Some fields are left blank when the metric cannot be computed safely, for example:

- no valid response times
- no trials in a time segment
- zero variance in the source data
- no comparable post-error and post-correct trials
- decrement metrics whose baseline value is zero

## Data Sheet Order

The `Data` tab now stores, in order:

1. Original session metadata and existing IES fields
2. Overall accuracy, median RT, RT variability, and lapse rate
3. First/second/third segment accuracy, median RT, RT CV, and lapse rate
4. Decrement indices
5. Time-on-task slopes
6. Post-error adjustment metrics
7. RT-success correlation
