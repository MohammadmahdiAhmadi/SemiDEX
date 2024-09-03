# Semi-Decentralized Exchange

This repository contains a subset of the codebase for [Valmart](https://valmart.net/) Exchange, a semi-decentralized cryptocurrency exchange platform similar to Uniswap. This project includes three key applications: `app_Swap_Pool`, `app_Swap_Providing`, and `app_Swap_Swaping`. These apps manage the core functionalities of the swap pools, liquidity providing, and swap history within the exchange.

**Note:** This repository only includes a part of the codebase and cannot be run as a standalone project due to missing dependencies and components. The content has been uploaded with explicit permission from the CEO of Valmart Exchange.

## Project Overview

### app_Swap_Pool
The `app_Swap_Pool` application handles the management of liquidity pools. It includes models for defining pools, managing their liquidity, and calculating important metrics such as prices, total value locked (TVL), and fees. The application also provides serializers and views to expose pool-related data via RESTful APIs.

### app_Swap_Providing
The `app_Swap_Providing` application manages liquidity providers who contribute to the pools. It allows users to add or remove liquidity and tracks their contributions through the `Provider` model. This app also includes serializers to validate and process provider transactions, as well as views to interact with the provider data.

### app_Swap_Swaping
The `app_Swap_Swaping` application records the history of swaps that occur within the pools. It manages swap transactions, calculates fees, and tracks swap activities. This app is essential for maintaining an accurate record of all swaps and providing dat a for analytics.

## Features

- **Liquidity Pool Management:** Create and manage swap pools, calculate prices, and track TVL.
- **Liquidity Provisioning:** Add or remove liquidity from pools, calculate provider shares, and manage provider history.
- **Swap History:** Record and analyze swap transactions within the pools, including fee calculations and swap tracking.

## Usage

This codebase is intended for educational and reference purposes. It provides insight into the structure and functionality of a semi-decentralized exchange but cannot function as a complete application without the missing components.

## License

This project is open-source and available under the [MIT License](https://opensource.org/licenses/MIT).
