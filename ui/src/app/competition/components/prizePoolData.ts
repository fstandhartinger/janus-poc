const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
});

const shortCurrencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const poolAmountUsd = 4250;

export const prizePoolSnapshot = {
  amountUsd: poolAmountUsd,
  amountDisplay: currencyFormatter.format(poolAmountUsd),
  amountShort: shortCurrencyFormatter.format(poolAmountUsd),
  accumulatingSince: 'Jan 15, 2026',
  daysAtTop: 8,
  champion: 'baseline-v3',
  miner: '5F3sa...7Kx2',
};
