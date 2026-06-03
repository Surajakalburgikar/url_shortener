# Brief.ly — Frontend Client

This is the React SPA frontend client for the **URL Shortener & Analytics Platform**. It is powered by Vite, structured using modern React components, and styled with a custom Vanilla CSS design system.

---

## 🎨 Highlights & Layouts
- **Minimalist Slate Theme**: Uses custom CSS variables inside `src/index.css` for a flat dark slate layout without glowing borders or purple gradients.
- **JWT Session Persistence**: Axios client automatically stores, attaches, and refreshes access/refresh tokens.
- **Interactive Dashboard Charts**: Leverages `Recharts` to display click frequency over the last 30 days, geographic tracking, and referrer origins.
- **Advanced Parameters**: Supports custom alias creation and custom expiration datetimes.
- **Responsive Layout**: Designed to render elegantly on all device screens.

---

## 🛠️ Getting Started

### 1. Requirements
Ensure you have Node.js (v18+) installed on your machine.

### 2. Installation
Navigate into the `frontend` directory and install the node dependencies:
```bash
npm install
```

### 3. Environment Setup
By default, the client points to `http://localhost:8000` (local backend address). If you deploy or host your backend on a custom port, configure it by creating a `.env` file in the `frontend` folder:
```env
VITE_API_BASE_URL=http://your-backend-api-domain.com
```

### 4. Running Locally
Run the Vite development server with Hot Module Replacement (HMR):
```bash
npm run dev
```
Open `http://localhost:5173` in your browser.

### 5. Production Compilation
Build the minified production assets inside the `/dist` directory:
```bash
npm run build
```
The production bundle is optimized and has code splitting enabled for performance.
