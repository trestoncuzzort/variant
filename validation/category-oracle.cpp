#include <boost/variant.hpp>
#include <boost/variant/multivisitors.hpp>
#include <type_traits>
#include <utility>
#include <iostream>

unsigned comparisons=0, mismatches=0;

template<class T> int category(T&&) { return !std::is_lvalue_reference<T&&>::value; }
struct functions {
    template<class T> int operator()(T&& a) const { return category(std::forward<T>(a)); }
    template<class T,class U> int operator()(T&& a,U&& b) const {
        return category(std::forward<T>(a))+2*category(std::forward<U>(b));
    }
    template<class T,class U,class V> int operator()(T&& a,U&& b,V&& c) const {
        return category(std::forward<T>(a))+2*category(std::forward<U>(b))+4*category(std::forward<V>(c));
    }
};
struct visitor : functions { typedef int result_type; };
struct deduced : functions {};

template<unsigned N> struct sample {
    typedef boost::variant<typename std::conditional<(N&1)!=0,int&,int>::type> variant;
    typedef typename std::conditional<(N&2)!=0,variant&&,variant&>::type argument;
    int value;
    variant v;
    sample():value(42),v(value){}
    argument get(){ return static_cast<argument>(v); }
    static int expected(){ return (N&1)==0 && (N&2)!=0 ? 1 : 0; }
};
void check(int actual,int expected){++comparisons;mismatches+=actual!=expected;}
template<unsigned N> struct cases {
    static void run(){
        sample<N/16> a;sample<(N/4)%4> b;sample<N%4> c;
        visitor f;
        check(boost::apply_visitor(f,a.get(),b.get(),c.get()),a.expected()+2*b.expected()+4*c.expected());
        if(N<16){
            check(boost::apply_visitor(f,b.get(),c.get()),b.expected()+2*c.expected());
#ifdef BOOST_VARIANT_HAS_DECLTYPE_APPLY_VISITOR_RETURN_TYPE
            deduced d;check(boost::apply_visitor(d,b.get(),c.get()),b.expected()+2*c.expected());
#endif
        }
        if(N<4){
            check(boost::apply_visitor(f,c.get()),c.expected());
#ifdef BOOST_VARIANT_HAS_DECLTYPE_APPLY_VISITOR_RETURN_TYPE
            deduced d;check(boost::apply_visitor(d,c.get()),c.expected());
#endif
        }
        cases<N-1>::run();
    }
};
template<> struct cases<0> {
    static void run(){
        sample<0> a,b,c;visitor f;
        check(boost::apply_visitor(f,a.get()),0);
        check(boost::apply_visitor(f,a.get(),b.get()),0);
        check(boost::apply_visitor(f,a.get(),b.get(),c.get()),0);
#ifdef BOOST_VARIANT_HAS_DECLTYPE_APPLY_VISITOR_RETURN_TYPE
        deduced d;check(boost::apply_visitor(d,a.get()),0);check(boost::apply_visitor(d,a.get(),b.get()),0);
#endif
    }
};
int main(){
    cases<63>::run();
    std::cout<<"{\"comparisons\":"<<comparisons<<",\"mismatches\":"<<mismatches<<"}\n";
    return mismatches?1:0;
}
