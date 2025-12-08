import React, { Component } from 'react';
import { createRoot } from 'react-dom/client';
import App from 'component/App'
import { Provider } from 'mobx-react';


if (module.hot) {
  module.hot.accept();
}

const container = document.getElementById("root");
const root = createRoot(container);
root.render(<App />);

