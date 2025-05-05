// webpack.config.js
'use strict';
const path = require('path');

module.exports = {
  entry: './src/index.ts',
  output: {
    filename: 'index.out.js',
    path: path.resolve(__dirname, 'lib'),
    libraryTarget: 'amd',
  },
  resolve: {
    extensions: ['.ts', '.js'],
    fallback: {
      fs: false,
    },
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      }
    ]
  },
  externals: [
    /^@jupyterlab\/.+$/,
    /^@lumino\/.+$/,
  ],
};

