import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import CartItem from '../components/CartItem';

export default function Cart() {
  const { items, subtotal, retailerId } = useCart();
  const navigate = useNavigate();

  if (items.length === 0) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Cart</h1>
        <p className="text-gray-500 mb-4">Your cart is empty.</p>
        <button
          onClick={() => navigate('/')}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
        >
          Browse Retailers
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Your Cart</h1>
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        {items.map((item) => (
          <CartItem key={item.product.id} item={item} />
        ))}
        <div className="flex items-center justify-between pt-4 mt-2 border-t border-gray-200">
          <span className="text-lg font-semibold text-gray-900">Subtotal</span>
          <span className="text-xl font-bold text-gray-900">
            ${subtotal.toFixed(2)}
          </span>
        </div>
      </div>
      <div className="flex gap-3 mt-4">
        <button
          onClick={() => navigate(`/products?retailer=${retailerId}`)}
          className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-50 text-sm font-medium"
        >
          Continue Shopping
        </button>
        <button
          onClick={() => navigate('/review')}
          className="flex-1 bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700 text-sm font-medium"
        >
          Review Order
        </button>
      </div>
    </div>
  );
}
