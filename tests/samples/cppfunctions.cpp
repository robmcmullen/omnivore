float TestClass::test1a(float arg) 
{
    printf("blah");
    switch (blah) {
      case 1: //blah
        stuff;
        stuff;
        goto blah;
        here;
      case 0:
      case 3:
      default:
        stuff;
blah:
        if (blah) {
            if (blah) {
                stuff;
            }
        }
    }
}

float TestClass::operator=(const float arg) 
{
    printf("blah");
}

float TestClass::operator()(const float arg) 
{
    printf("blah");
}

float TestClass::operator+(const float arg) 
{
    printf("blah");
}

class blah :: public blah {
  public:
    int blah;
  private:
    int blah;
}

float TestClass::test1b(const float arg) 
{
    printf("blah");
}


float TestClass::test1c(const float arg) const
{
    printf("blah");
}


float TestClass::test1c(const float& arg) const
{
    printf("blah");
}


//After comments
float TestClass::test2a(const float& arg)
{
    printf("blah");
}

// this is commented_out (should not appear)
float TestClass::test2b(const float& arg) const
{
    printf("blah");
}

/*
 * this is commented_out (should not appear)
 */
float TestClass::test2c(const float& arg) const
{
    printf("blah");
}

float* TestClass::test3a(const float& arg)
{
    printf("blah");
}

float* TestClass::test3b(const float& arg) const
{
    printf("blah");
}

float** TestClass::test3c(const float& arg) const
{
    printf("blah");
}

float * TestClass::test3d(const float& arg)
{
    printf("blah");
}

float ** TestClass::test3e(const float& arg)
{
    printf("blah");
}

float *** TestClass::test3f(const float& arg)
{
    printf("blah");
}

float& TestClass::test3g(const float& arg)
{
    return 0.0;
}

float & TestClass::test3h(const float& arg)
{
    return 0.0;
}


int32_t TestClass::test4a(float arg)
{
    printf("blah");
}

int32_t* TestClass::test4b(const float& arg) const
{
    printf("blah");
}

int32_t* TestClass::test4c(const float& arg) const
{
    if (stuff) {
        stuff;
    }
}

int32_t* TestClass::test4d(const float& arg) const
{
    if should_not_be_listed(stuff) {
        stuff;
    }
}

class TestClass {
    int test5a(int arg) {
        printf("blah");
    }
}

const float& Stuff::Things(const Gunk *Crud) {
    stuff;
}

const float& Things(const int *Crud) {
    stuff;
}

template<class PixelT> int Band<PixelT>::Blur(const int& k_size) {
    stuff;
}
