import { createContext, useContext, useState } from 'react';

const CartContext = createContext();

export function CartProvider({ children }) {
  const [items, setItems] = useState([]);
  const [retailerId, setRetailerId] = useState(null);

  const addItem = (product, qty = 1) => {
    setItems((prev) => {
      const existing = prev.find((i) => i.product.id === product.id);
      if (existing) {
        return prev.map((i) =>
          i.product.id === product.id ? { ...i, quantity: i.quantity + qty } : i
        );
      }
      return [...prev, { product, quantity: qty }];
    });
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeItem(productId);
      return;
    }
    setItems((prev) =>
      prev.map((i) => (i.product.id === productId ? { ...i, quantity } : i))
    );
  };

  const removeItem = (productId) => {
    setItems((prev) => prev.filter((i) => i.product.id !== productId));
  };

  const clearCart = () => {
    setItems([]);
    setRetailerId(null);
  };

  const startOrder = (rid) => {
    if (retailerId && retailerId !== rid) {
      setItems([]);
    }
    setRetailerId(rid);
  };

  const subtotal = items.reduce(
    (sum, i) => sum + i.product.unit_price * i.quantity,
    0
  );

  return (
    <CartContext.Provider
      value={{
        items,
        retailerId,
        addItem,
        updateQuantity,
        removeItem,
        clearCart,
        startOrder,
        subtotal,
        itemCount: items.length,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);
