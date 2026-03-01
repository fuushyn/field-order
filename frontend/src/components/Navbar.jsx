import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

export default function Navbar() {
  const { rep, logout } = useAuth();
  const { itemCount } = useCart();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-blue-700 text-white shadow-md">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold tracking-tight">
          Field Order
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/" className="hover:text-blue-200 text-sm">Retailers</Link>
          <Link to="/orders" className="hover:text-blue-200 text-sm">Orders</Link>
          <Link to="/cart/from-text" className="hover:text-blue-200 text-sm">📷 Smart Order</Link>
          <Link to="/cart" className="hover:text-blue-200 text-sm relative">
            Cart
            {itemCount > 0 && (
              <span className="absolute -top-2 -right-4 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                {itemCount}
              </span>
            )}
          </Link>
          <span className="text-sm text-blue-200 ml-2">{rep?.name}</span>
          <button onClick={handleLogout} className="text-sm bg-blue-800 hover:bg-blue-900 px-3 py-1 rounded">Logout</button>
        </div>
      </div>
    </nav>
  );
}
