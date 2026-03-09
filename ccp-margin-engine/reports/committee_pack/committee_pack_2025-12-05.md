# Monthly Risk Committee Pack
**Period:** 2025-11-05 00:00:00 to 2025-12-05 00:00:00

## 1. Margin Trend
*(See attached chart – total required margin by day)*

## 2. Top Stressed Members
| Member | Type | Avg Coverage | Min Coverage | Red Days |
|--------|------|-------------|-------------|----------|
| MBR_009 | weak_liquidity | 59.75% | 52.00% | 4 |
| MBR_003 | directional_macro | 70.00% | 65.00% | 4 |
| MBR_010 | directional_macro | 85.00% | 82.00% | 4 |
| MBR_001 | directional_macro | 88.00% | 83.00% | 4 |
| MBR_002 | directional_macro | 92.75% | 85.00% | 4 |

## 3. Coverage Ratio Distribution
- Mean: 107.50%
- Std: 0.5489
- Min: 52.00%
- Max: 321.00%

## 4. Backtesting Summary – 1 exceptions
- MBR_004: 1 exceptions
- MBR_001: 0 exceptions
- MBR_002: 0 exceptions
- MBR_003: 0 exceptions
- MBR_005: 0 exceptions

## 5. Concentration Events: 0

## 6. Known Limitations
- Stylised margin formula, not a real CCP methodology
- Simplified liquidation assumptions
- Limited product universe (equity/rates futures, listed options)
- Simplified collateral eligibility and haircut structure
- No auction/default management simulation
- No legal segregation/account structure modelling
- Scenario set may omit some cross-asset contagion channels

## 7. Recommended Actions
- Review margin call triggers for red-flagged members
- Validate stressed VaR calibration against recent vol regime
- Confirm concentration add-on thresholds remain appropriate
- Investigate any stale data sources flagged in weekly reports