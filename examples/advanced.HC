#define MAX 16
#define SQ(x) ((x)*(x))

class Vec2
{
  I64 x;
  I64 y;
};

I64 Dot(Vec2 *a, Vec2 *b)
{
  return a->x * b->x + a->y * b->y;
}

I64 Main()
{
  I64 sum = 0;
  I64 i;

  for (i = 0; i < MAX; i = i + 1)
  {
    sum = sum + SQ(i);
  }

  switch (sum)
  {
    case 0:
      $("sum is zero\n");
      break;
    default:
      $("sum = %d\n", sum);
      break;
  }

  Vec2 a;
  Vec2 b;
  a.x = 3;
  a.y = 4;
  b.x = 1;
  b.y = 2;
  $("dot = %d\n", Dot(&a, &b));

  for (I64 k : 0..5)
  {
    $("k=%d\n", k);
  }

  return 0;
}