#include <boost/variant.hpp>
#include <iostream>
#include <type_traits>
#include <utility>

struct category : boost::static_visitor<int> {
    template<class T> int operator()(T&&) const {
        return !std::is_lvalue_reference<T&&>::value
            + 2 * std::is_const<typename std::remove_reference<T>::type>::value;
    }
};

int main()
{
    int v = 42;
    const int cv = 43;
    boost::variant<int> owned(v);
    const boost::variant<int> const_owned(v);
    boost::variant<int&> borrowed(v);
    const boost::variant<int&> const_borrowed(v);
    boost::variant<const int&> borrowed_const(cv);
    const boost::variant<const int&> const_borrowed_const(cv);
    category visitor;
    const int actual[] = {
        boost::apply_visitor(visitor, owned),
        boost::apply_visitor(visitor, std::move(owned)),
        boost::apply_visitor(visitor, const_owned),
        boost::apply_visitor(visitor, std::move(const_owned)),
        boost::apply_visitor(visitor, borrowed),
        boost::apply_visitor(visitor, std::move(borrowed)),
        boost::apply_visitor(visitor, const_borrowed),
        boost::apply_visitor(visitor, std::move(const_borrowed)),
        boost::apply_visitor(visitor, borrowed_const),
        boost::apply_visitor(visitor, std::move(borrowed_const)),
        boost::apply_visitor(visitor, const_borrowed_const),
        boost::apply_visitor(visitor, std::move(const_borrowed_const))
    };
    const int expected[] = {0,1,2,3,0,0,0,0,2,2,2,2};
    int failures = 0;
    for (unsigned i = 0; i < 12; ++i) {
        std::cout << actual[i] << (i == 11 ? '\n' : ' ');
        failures += actual[i] != expected[i];
    }
    return failures;
}
