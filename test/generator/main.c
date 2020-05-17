#include <stdio.h>

int main()
{
#ifdef TEST_STRING
  puts(TEST_STRING);
#endif
}
