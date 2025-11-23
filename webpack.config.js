const path = require('path');
const BundleTracker = require('webpack-bundle-tracker');
const webpack = require('webpack');

module.exports = (env, argv) => {
  const isDev = argv.mode === 'development';

  return {
    entry: {
      index: path.resolve('./src/js/index'),
      legacy: path.resolve('./src/js/legacy-index')
    },
    mode: isDev ? 'development' : 'production',
    output: {
      path: path.resolve('./src/bundles/'),
      filename: '[name]-[fullhash].js',
      publicPath: isDev ? 'http://localhost:3000/assets/bundles/' : '/static/bundles/',
      clean: true,
    },

    devServer: {
      host: '0.0.0.0',
      port: 3000,
      hot: true,
      headers: { "Access-Control-Allow-Origin": "*" },
      allowedHosts: 'all',
      client: {
        overlay: true,
      },
    },

    optimization: {
      splitChunks: {
        chunks: 'all',
      },
    },

    resolve: {
      alias: {
        state: path.resolve(__dirname, 'src/js/state'),
        component: path.resolve(__dirname, 'src/js/component'),
        panel: path.resolve(__dirname, 'src/js/component/panel'),
        api: path.resolve(__dirname, 'src/js/api'),
        constant: path.resolve(__dirname, 'src/js/constant'),
        styled: path.resolve(__dirname, 'src/js/styled')
      },
      extensions: ['.js', '.jsx']
    },

    plugins: [
      new BundleTracker({
        path: __dirname,
        filename: 'webpack-stats.json'
      }),
      new webpack.HotModuleReplacementPlugin(),
    ],

    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                '@babel/preset-env',
                '@babel/preset-react'
              ],
              plugins: [
                ['@babel/plugin-proposal-decorators', { legacy: true }],
                ['@babel/plugin-proposal-class-properties', { loose: true }],
                '@babel/plugin-proposal-object-rest-spread'
              ]
            }
          }
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ]
    }
  };
};
