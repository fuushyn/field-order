import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api';

export default function OrderConfirmation() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);

  useEffect(() => {
    api.get(`/orders/${id}`).then(({ data }) => setOrder(data));
  }, [id]);

  if (!order) return <p className="p-6 text-gray-500">Loading...</p>;

  return (
    <div className="max-w-2xl mx-auto p-6 text-center">
      <div className="bg-green-50 border border-green-200 rounded-lg p-8 mb-6">
        <div className="text-4xl mb-3">&#10003;</div>
        <h1 className="text-2xl font-bold text-green-800 mb-2">
          Order Submitted!
        </h1>
        <p className="text-green-700">
          Order <span className="font-mono font-bold">#{order.id}</span> has
          been placed successfully.
        </p>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg p-5 text-left mb-6">
        <h2 className="font-semibold text-gray-900 mb-3">Order Summary</h2>
        <p className="text-sm text-gray-600 mb-1">
          <span className="font-medium">Retailer:</span> {order.retailer_name}
        </p>
        <p className="text-sm text-gray-600 mb-3">
          <span className="font-medium">Status:</span>{' '}
          <span className="capitalize">{order.status}</span>
        </p>
        <ul className="space-y-1 mb-3">
          {order.items.map((item) => (
            <li
              key={item.id}
              className="text-sm flex justify-between text-gray-700"
            >
              <span>
                {item.product_name} x{item.quantity}
              </span>
              <span>${item.subtotal.toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <div className="flex justify-between pt-2 border-t border-gray-200 font-semibold">
          <span>Total</span>
          <span>${order.total.toFixed(2)}</span>
        </div>
      </div>
      <div className="flex gap-3 justify-center">
        <Link
          to="/orders"
          className="bg-blue-600 text-white px-5 py-2 rounded-md hover:bg-blue-700 text-sm font-medium"
        >
          View All Orders
        </Link>
        <Link
          to="/"
          className="border border-gray-300 text-gray-700 px-5 py-2 rounded-md hover:bg-gray-50 text-sm font-medium"
        >
          Back to Retailers
        </Link>
      </div>
    </div>
  );
}
