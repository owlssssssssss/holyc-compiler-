I64 Fib(I64 n)
{
  if (n <= 1)
    return n;
  return Fib(n - 1) + Fib(n - 2);
}

I64 Main()
{
  I64 i;
  for (i = 0; i < 10; i = i + 1)
  {
    $("fib(%d) = %d\n", i, Fib(i));
  }
  return 0;
}