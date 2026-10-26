#include <boost/variant.hpp>
#include <cassert>

struct Changer : boost::static_visitor<void> {
    void operator()(int& v) const { v += 10; }
    void operator()(double& v) const { v += 20; }
};

int main()
{
    int i = 0;
    double d = 0;
    Changer visitor;
    typedef boost::variant<int&, double&> variant;
    variant v(i);
    boost::apply_visitor(visitor, v);
    boost::apply_visitor(visitor, variant(d));
    assert(i == 10 && d == 20);
}
