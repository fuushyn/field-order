import { useCart } from '../context/CartContext';

export default function CartItem({ item }) {
  const { updateQuantity, removeItem } = useCart();
  const { product, quantity } = item;

  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100">
      <div className="flex-1">
        <p className="font-medium text-gray-900">{product.name}</p>
        <p className="text-sm text-gray-500">
          ${product.unit_price.toFixed(2)} / {product.unit}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => updateQuantity(product.id, quantity - 1)}
          className="w-8 h-8 rounded bg-gray-100 hover:bg-gray-200 text-lg font-bold"
        >
          -
        </button>
        <span className="w-8 text-center font-medium">{quantity}</span>
        <button
          onClick={() => updateQuantity(product.id, quantity + 1)}
          className="w-8 h-8 rounded bg-gray-100 hover:bg-gray-200 text-lg font-bold"
        >
          +
        </button>
      </div>
      <p className="w-24 text-right font-semibold text-gray-900">
        ${(product.unit_price * quantity).toFixed(2)}
      </p>
      <button
        onClick={() => removeItem(product.id)}
        className="ml-4 text-red-500 hover:text-red-700 text-sm"
      >
        Remove
      </button>
    </div>
  );
}
