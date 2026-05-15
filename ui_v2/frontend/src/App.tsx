import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import LogWindow from './components/layout/LogWindow';
import { LogWindowProvider } from './contexts/LogWindowContext';
import Dashboard from './pages/Dashboard';
import BotDetail from './pages/BotDetail';
import RunningBot from './pages/RunningBot';
import ItemDatabase from './pages/ItemDatabase';

export default function App() {
  return (
    <LogWindowProvider>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/bot/:botId" element={<BotDetail />} />
            <Route path="/running" element={<RunningBot />} />
            <Route path="/items" element={<ItemDatabase />} />
          </Routes>
        </main>
        <LogWindow />
      </div>
    </LogWindowProvider>
  );
}
