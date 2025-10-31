import type { Metadata } from 'next';
import Dashboard from '@/components/Dashboard';

export const metadata: Metadata = {
  title: 'Dashboard - Thalas Trader',
  description: 'Multi-LLM consensus trading dashboard with real-time bot management and performance tracking',
};

export default function DashboardPage() {
  return <Dashboard />;
}
