import { useCart } from '../context/CartContext';

export default function ProductCard({ product }) {
  const { addItem } = useCart();

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-400 font-mono">{product.sku}</span>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
            {product.category}
          </span>
        </div>
        <h3 className="font-semibold text-gray-900 mb-1">{product.name}</h3>
        <p className="text-blue-700 font-bold text-lg">
          ${product.unit_price.toFixed(2)}{' '}
          <span className="text-sm text-gray-500 font-normal">/ {product.unit}</span>
        </p>
      </div>
      <button
        onClick={() => addItem(product)}
        disabled={!product.in_stock}
        className={`mt-3 w-full py-2 rounded text-sm font-medium ${
          product.in_stock
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
        }`}
      >
        {product.in_stock ? 'Add to Cart' : 'Out of Stock'}
      </button>
    </div>
  );
}
