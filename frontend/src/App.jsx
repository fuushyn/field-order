import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { CartProvider } from './context/CartContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import RetailerList from './pages/RetailerList';
import RetailerDetail from './pages/RetailerDetail';
import ProductCatalog from './pages/ProductCatalog';
import Cart from './pages/Cart';
import OrderReview from './pages/OrderReview';
import OrderConfirmation from './pages/OrderConfirmation';
import OrderHistory from './pages/OrderHistory';
import CartFromText from './pages/CartFromText';

function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      {children}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <CartProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><AppLayout><RetailerList /></AppLayout></ProtectedRoute>} />
            <Route path="/retailers/:id" element={<ProtectedRoute><AppLayout><RetailerDetail /></AppLayout></ProtectedRoute>} />
            <Route path="/products" element={<ProtectedRoute><AppLayout><ProductCatalog /></AppLayout></ProtectedRoute>} />
            <Route path="/cart" element={<ProtectedRoute><AppLayout><Cart /></AppLayout></ProtectedRoute>} />
            <Route path="/review" element={<ProtectedRoute><AppLayout><OrderReview /></AppLayout></ProtectedRoute>} />
            <Route path="/confirmation/:id" element={<ProtectedRoute><AppLayout><OrderConfirmation /></AppLayout></ProtectedRoute>} />
            <Route path="/orders" element={<ProtectedRoute><AppLayout><OrderHistory /></AppLayout></ProtectedRoute>} />
            <Route path="/orders/:id" element={<ProtectedRoute><AppLayout><OrderConfirmation /></AppLayout></ProtectedRoute>} />
            <Route path="/cart/from-text" element={<ProtectedRoute><AppLayout><CartFromText /></AppLayout></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </CartProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
