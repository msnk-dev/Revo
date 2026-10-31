type MoneyProps = { amount: string; currency?: string; locale?: string; className?: string };

export function Money({ amount, currency = "INR", locale = "en-IN", className }: MoneyProps) {
  const match = /^(-?\d+)(?:\.(\d+))?$/.exec(amount);
  if (!match) throw new Error(`Invalid decimal amount: ${amount}`);
  const [, whole = "0", fraction = ""] = match;
  const wholeValue = BigInt(whole);
  const groupedWhole = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(wholeValue);
  const currencyParts = new Intl.NumberFormat(locale, { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).formatToParts(0);
  const rendered = currencyParts.map((part) => {
    if (part.type === "integer") return groupedWhole;
    if (part.type === "fraction") return fraction.padEnd(2, "0").slice(0, 2);
    return part.value;
  }).join("");
  return <span className={className}>{rendered}</span>;
}
