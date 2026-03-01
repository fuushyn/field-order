import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { useCart } from '../context/CartContext';
import ProductCard from '../components/ProductCard';

export default function ProductCatalog() {
  const [searchParams] = useSearchParams();
  const retailerParam = searchParams.get('retailer');
  const isReorder = searchParams.get('reorder') === 'true';
  const navigate = useNavigate();
  const { addItem, retailerId, startOrder, itemCount } = useCart();

  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(true);

  // Ensure cart is scoped to the right retailer
  useEffect(() => {
    if (retailerParam) {
      startOrder(Number(retailerParam));
    }
  }, [retailerParam]);

  // Handle reorder: add items from session storage
  useEffect(() => {
    if (isReorder && products.length > 0) {
      const reorderData = sessionStorage.getItem('reorder');
      if (reorderData) {
        const items = JSON.parse(reorderData);
        const productMap = Object.fromEntries(products.map((p) => [p.id, p]));
        items.forEach(({ productId, quantity }) => {
          const product = productMap[productId];
          if (product) addItem(product, quantity);
        });
        sessionStorage.removeItem('reorder');
      }
    }
  }, [isReorder, products]);

  useEffect(() => {
    api.get('/products/categories').then(({ data }) => setCategories(data));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      api
        .get('/products', { params: { search, category } })
        .then(({ data }) => {
          setProducts(data);
          setLoading(false);
        });
    }, 200);
    return () => clearTimeout(timer);
  }, [search, category]);

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        {itemCount > 0 && (
          <button
            onClick={() => navigate('/cart')}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm font-medium"
          >
            View Cart ({itemCount})
          </button>
        )}
      </div>
      <div className="flex gap-3 mb-6">
        <input
          type="text"
          placeholder="Search products..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((p) => (
            <ProductCard key={p.id} product={p} />
          ))}
        </div>
      )}
    </div>
  );
}
