import { Link } from 'react-router-dom';

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  delivered: 'bg-green-100 text-green-800',
};

export default function OrderCard({ order }) {
  return (
    <Link
      to={`/orders/${order.id}`}
      className="block bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-gray-900">Order #{order.id}</span>
        <span
          className={`text-xs font-medium px-2.5 py-0.5 rounded capitalize ${
            statusColors[order.status] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {order.status}
        </span>
      </div>
      <p className="text-sm text-gray-600">{order.retailer_name}</p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-sm text-gray-500">
          {new Date(order.created_at).toLocaleDateString()}
        </span>
        <span className="font-semibold text-gray-900">
          ${order.total.toFixed(2)}
        </span>
      </div>
    </Link>
  );
}
