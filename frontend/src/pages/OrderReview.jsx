import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useCart } from '../context/CartContext';

export default function OrderReview() {
  const { items, subtotal, retailerId, clearCart } = useCart();
  const navigate = useNavigate();
  const [retailer, setRetailer] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!retailerId || items.length === 0) {
      navigate('/cart');
      return;
    }
    api.get(`/retailers/${retailerId}`).then(({ data }) => setRetailer(data));
  }, [retailerId]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      const { data } = await api.post('/orders', {
        retailer_id: retailerId,
        items: items.map((i) => ({
          product_id: i.product.id,
          quantity: i.quantity,
        })),
      });
      clearCart();
      navigate(`/confirmation/${data.id}`);
    } catch {
      setError('Failed to submit order. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!retailer) return <p className="p-6 text-gray-500">Loading...</p>;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Review Order</h1>
      {error && (
        <div className="bg-red-50 text-red-600 text-sm p-3 rounded mb-4">
          {error}
        </div>
      )}
      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-4">
        <h2 className="font-semibold text-gray-900 mb-1">Retailer</h2>
        <p className="text-gray-700">{retailer.name}</p>
        <p className="text-sm text-gray-500">{retailer.address}</p>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-5 mb-4">
        <h2 className="font-semibold text-gray-900 mb-3">Items</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-gray-500">
              <th className="pb-2">Product</th>
              <th className="pb-2 text-center">Qty</th>
              <th className="pb-2 text-right">Price</th>
              <th className="pb-2 text-right">Subtotal</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.product.id} className="border-b border-gray-50">
                <td className="py-2 text-gray-900">{item.product.name}</td>
                <td className="py-2 text-center">{item.quantity}</td>
                <td className="py-2 text-right">
                  ${item.product.unit_price.toFixed(2)}
                </td>
                <td className="py-2 text-right font-medium">
                  ${(item.product.unit_price * item.quantity).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex justify-between pt-3 mt-2 border-t border-gray-200">
          <span className="font-semibold text-gray-900">Total</span>
          <span className="text-xl font-bold text-gray-900">
            ${subtotal.toFixed(2)}
          </span>
        </div>
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => navigate('/cart')}
          className="flex-1 border border-gray-300 text-gray-700 py-2 rounded-md hover:bg-gray-50 text-sm font-medium"
        >
          Back to Cart
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="flex-1 bg-green-600 text-white py-2 rounded-md hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
        >
          {submitting ? 'Submitting...' : 'Submit Order'}
        </button>
      </div>
    </div>
  );
}
