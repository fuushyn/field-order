import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { useCart } from '../context/CartContext';
import OrderCard from '../components/OrderCard';

export default function RetailerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { startOrder, clearCart, retailerId } = useCart();
  const [retailer, setRetailer] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get(`/retailers/${id}`),
      api.get('/orders', { params: { retailer_id: id } }),
    ]).then(([retRes, ordRes]) => {
      setRetailer(retRes.data);
      setOrders(ordRes.data);
      setLoading(false);
    });
  }, [id]);

  const handleNewOrder = () => {
    startOrder(Number(id));
    navigate(`/products?retailer=${id}`);
  };

  const handleReorder = async (order) => {
    startOrder(Number(id));
    clearCart();
    const { data } = await api.get(`/orders/${order.id}`);
    sessionStorage.setItem(
      'reorder',
      JSON.stringify(data.items.map((i) => ({ productId: i.product_id, quantity: i.quantity })))
    );
    navigate(`/products?retailer=${id}&reorder=true`);
  };

  if (loading) return <p className="p-6 text-gray-500">Loading...</p>;
  if (!retailer) return <p className="p-6 text-gray-500">Retailer not found.</p>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{retailer.name}</h1>
        <p className="text-gray-600 mt-1">{retailer.address}</p>
        {retailer.contact_phone && (
          <p className="text-gray-600">{retailer.contact_phone}</p>
        )}
        {retailer.contact_email && (
          <p className="text-gray-600">{retailer.contact_email}</p>
        )}
        <div className="flex gap-3 mt-4">
          <button
            onClick={handleNewOrder}
            className="bg-blue-600 text-white px-5 py-2 rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            New Order
          </button>
        </div>
      </div>

      <h2 className="text-lg font-semibold text-gray-900 mb-3">Past Orders</h2>
      {orders.length === 0 ? (
        <p className="text-gray-500">No orders yet.</p>
      ) : (
        <div className="grid gap-3">
          {orders.map((o) => (
            <div key={o.id} className="flex items-start gap-3">
              <div className="flex-1">
                <OrderCard order={o} />
              </div>
              <button
                onClick={() => handleReorder(o)}
                className="mt-2 text-sm text-blue-600 hover:text-blue-800 whitespace-nowrap"
              >
                Reorder
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
