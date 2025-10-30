# thalas_trader
TRADING BOT
This project provides a clean, intuitive, and feature-rich user interface for interacting with a Freqtrade instance. While Freqtrade is a powerful headless trading bot, this dashboard aims to give users a comprehensive visual overview of their trading operations, from high-level portfolio performance down to individual bot status and recent trades.
The interface is designed to be fast, responsive, and easy to navigate, providing critical information at a glance.
Key Features
At-a-Glance Summary: Key performance indicators (KPIs) like total profit, 24h profit, active bot count, and trade volume are prominently displayed.
Portfolio Performance Chart: Visualize your portfolio's growth over time with an interactive and beautifully rendered area chart.
Real-time Bot Status: Monitor all your active and inactive bots in a detailed table. Check their status (Running, Stopped, Error), assigned strategy, current pair, and profit/loss metrics.
Recent Trades Feed: Instantly see the latest buy and sell orders executed by your bots, complete with pair, type, amount, price, and realized profit.
Responsive Design: A mobile-first approach ensures the dashboard looks great and is fully functional on any device, from a large monitor to a smartphone.
Modern Tech Stack: Built with the latest frontend technologies for a fast, reliable, and maintainable application.
Built With
This project is built upon a modern and robust frontend stack:
React - A JavaScript library for building user interfaces.
TypeScript - A typed superset of JavaScript that compiles to plain JavaScript.
Tailwind CSS - A utility-first CSS framework for rapid UI development.
Recharts - A composable charting library built on React components.
Getting Started
To get a local copy up and running, follow these simple steps.
Prerequisites
Make sure you have Node.js and npm (or yarn) installed on your machine.
npm
code
Sh
npm install npm@latest -g
Installation
Clone the repo
code
Sh
git clone https://github.com/your_username/freqtrade-ui-dashboard.git
Navigate to the project directory
code
Sh
cd freqtrade-ui-dashboard
Install NPM packages
code
Sh
npm install
Start the development server
code
Sh
npm run dev
Open http://localhost:3000 to view it in the browser.
Project Structure
The codebase is organized into a clear and logical structure:
code
Code
/
├── components/         # Reusable React components
│   ├── BotStatusTable.tsx
│   ├── Dashboard.tsx
│   ├── Header.tsx
│   ├── PerformanceChart.tsx
│   ├── RecentTrades.tsx
│   ├── Sidebar.tsx
│   └── SummaryCard.tsx
│
├── data/               # Mock data for development
│   └── mockData.ts
│
├── public/             # Static assets
│
├── App.tsx             # Main application component
├── constants.tsx       # Shared constants (e.g., icons)
├── index.html          # The main HTML file
├── index.tsx           # The entry point of the React app
├── types.ts            # TypeScript type definitions
└── ...
Connecting to Freqtrade
This is a frontend-only application. Currently, it operates using mock data located in the data/mockData.ts file.
To connect this dashboard to a live Freqtrade instance, you will need to:
Set up a Backend/API: Create a backend service (e.g., using Node.js/Express, Python/Django) that communicates with your Freqtrade bot's API or RPC endpoints.
Implement API Endpoints: The backend should expose RESTful API endpoints that the frontend can call to fetch live data (e.g., /api/summary, /api/bots, /api/trades).
Update Frontend Services: Modify the components in this project to fetch data from your new API endpoints instead of the mock data source. You can use libraries like fetch or axios for this purpose.
Contributing
Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.
If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
License
Distributed under the MIT License. See LICENSE for more information.
