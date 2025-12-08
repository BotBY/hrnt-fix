import React, { Component, createRef } from 'react';



class ScrollObserver extends Component {
    constructor(props) {
        super(props);
        this.observerRef = createRef();
        this.io = null;
    }

    render() {
        return <div ref={this.observerRef}>{this.props.children}</div>
    }

    componentDidMount() {
        const options = {
            threshold: 1.0
        }
        const callback = (entries) => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    this.props.isIntersecting()
                }
            })
        }
        this.io = new IntersectionObserver(callback, options)
        if (this.observerRef.current) {
            this.io.observe(this.observerRef.current)
        }
    }

    componentWillUnmount() {
        if (this.io) {
            this.io.disconnect();
        }
    }
}

export default ScrollObserver