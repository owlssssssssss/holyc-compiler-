// Minimal HolyC standard library header

I64 Abs(I64 x)
{
  return x < 0 ? -x : x;
}

I64 Max(I64 a, I64 b)
{
  return a > b ? a : b;
}

I64 Min(I64 a, I64 b)
{
  return a < b ? a : b;
}