class Point
{
  I64 x;
  I64 y;
};

I64 DistSq(Point *p)
{
  return p->x * p->x + p->y * p->y;
}

I64 Main()
{
  Point p;
  p.x = 3;
  p.y = 4;
  $("Distance squared = %d\n", DistSq(&p));
  return 0;
}