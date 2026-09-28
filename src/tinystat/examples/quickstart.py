"""Confidence interval for a small sample, end to end."""

import tinystat

# Six measurements of the same part, in millimetres.
sample = [10.2, 10.4, 10.1, 10.3, 10.2, 10.5]

low, high = tinystat.confidence_interval(sample, alpha=0.05)
print(f"mean        {tinystat.mean(sample):.3f}")
print(f"95% CI      {low:.3f} to {high:.3f}")
print(f"t*(5, .05)  {tinystat.t_critical(5, 0.05)}")

if __name__ == "__main__":
    pass
