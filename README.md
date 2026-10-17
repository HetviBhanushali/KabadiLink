# ♻️ KabadiLink

**Making recycling easier, one pickup at a time.**

KabadiLink is a digital waste management platform connecting households, waste collectors, and recyclers. It streamlines recyclable waste collection through pickup scheduling, collection tracking, transparent payouts, and Green Points rewards.

## ✨ Features

- **Household Dashboard** — Schedule pickups and track collection progress.
- **Collector Dashboard** — Accept requests, manage pickups, and record waste weights.
- **Recycler Marketplace** — Explore and purchase recyclable material lots.
- **Green Points & Rewards** — Earn points through responsible recycling.
- **Admin Dashboard** — Monitor users, pickups, platform activity, and reward configurations.
- **Interactive Simulator** — Experience connected household and collector workflows through dual-phone interfaces.

## 🔄 How It Works

1. Households schedule waste collection.
2. Collectors accept requests and update pickup status.
3. Collected waste is weighed and payouts are calculated.
4. Households earn Green Points and redeem rewards.
5. Recyclers access available recyclable materials.

## 🛠️ Tech Stack

- **Frontend:** React 18, TypeScript, Vite, React Router
- **Backend:** Python 3.12, AWS SAM, AWS Lambda, API Gateway
- **Database:** Amazon DynamoDB
- **Development Tools:** Node.js, npm, AWS CLI, AWS SAM CLI

## 🚀 Getting Started

### Prerequisites

- Git
- Node.js and npm
- Python 3.12
- AWS CLI and AWS SAM CLI (for backend deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/HetviBhanushali/KabadiLink.git
cd KabadiLink
```

### 2. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed in your terminal, usually `http://localhost:5173`.

The frontend currently runs in demo mode using mock data persisted in browser `localStorage`.

### 3. Deploy the Backend (Optional)

Configure your AWS credentials and install the AWS SAM CLI. Then run:

```bash
cd ../backend
sam build
sam deploy --guided
```

Follow the prompts to configure your deployment. Once deployed, use the `ApiBaseUrl` output to access the API.

**Note:** The backend is a prototype and is not yet fully integrated with the frontend. Authentication and production-grade authorization are not implemented.

## 🌱 Our Mission

To build a more accessible, transparent, and rewarding recycling ecosystem by connecting communities with waste collection and recycling services.