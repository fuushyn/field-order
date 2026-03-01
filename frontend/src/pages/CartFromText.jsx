import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import api from '../api';

function matchBadge(matchType, confidence) {
  if (matchType === 'exact') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800">✓ Exact match</span>;
  if (matchType === 'fuzzy') return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-yellow-100 text-yellow-800">~ Fuzzy match ({Math.round(confidence * 100)}%)</span>;
  return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800">✗ Not found</span>;
}

function rowBg(matchType) {
  if (matchType === 'exact') return 'bg-green-50 border-green-200';
  if (matchType === 'fuzzy') return 'bg-yellow-50 border-yellow-200';
  return 'bg-red-50 border-red-200';
}

export default function CartFromText() {
  const [text, setText] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('text');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [ocrRawText, setOcrRawText] = useState('');
  const fileInputRef = useRef(null);
  const { addItem } = useCart();
  const navigate = useNavigate();

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setResults(null); setOcrRawText(''); setError('');
  };

  const handleGenerate = async () => {
    setLoading(true); setError(''); setResults(null); setOcrRawText('');
    try {
      if (mode === 'image') {
        if (!imageFile) return;
        const formData = new FormData();
        formData.append('file', imageFile);
        const { data } = await api.post('/cart/from-image', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
        setOcrRawText(data.raw_text);
        setResults(data.cart);
      } else {
        if (!text.trim()) return;
        const { data } = await api.post('/cart/parse-text', { text });
        setResults(data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process order. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = () => {
    if (!results) return;
    results.cart_items.filter(i => i.match_type !== 'not_found' && i.product).forEach(i => addItem(i.product, i.quantity));
    navigate('/cart');
  };

  const matchedCount = results ? results.cart_items.filter(i => i.match_type !== 'not_found' && i.product).length : 0;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Generate Cart from Order Note</h1>
      <p className="text-sm text-gray-500 mb-6">
        Upload a photo of a handwritten order note or paste text. OCR + fuzzy matching auto-populate your cart.
      </p>

      <div className="flex gap-2 mb-6">
        <button onClick={() => setMode('text')} className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${mode === 'text' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>
          📝 Paste Text
        </button>
        <button onClick={() => setMode('image')} className={`px-4 py-2 text-sm font-medium rounded-lg border transition-colors ${mode === 'image' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}>
          📷 Upload Image (OCR)
        </button>
      </div>

      {mode === 'text' ? (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Order text</label>
          <textarea
            className="w-full border border-gray-300 rounded-lg p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
            rows={7}
            placeholder={"10x Cola Classic 24-pack\n5x Orange Juice 12-pack\n3x Whole Milk 1 Gallon"}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
      ) : (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Handwritten order image</label>
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            {imagePreview
              ? <img src={imagePreview} alt="Order note preview" className="max-h-64 mx-auto rounded shadow" />
              : <div className="text-gray-400"><div className="text-4xl mb-2">📷</div><div className="text-sm">Click to upload image (PNG, JPG)</div></div>
            }
          </div>
          <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleImageChange} />
          {ocrRawText && (
            <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="text-xs font-medium text-gray-500 mb-1">OCR Extracted Text:</div>
              <pre className="text-xs text-gray-700 whitespace-pre-wrap font-mono">{ocrRawText}</pre>
            </div>
          )}
        </div>
      )}

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}

      <div className="flex gap-3 mb-8">
        <button
          onClick={handleGenerate}
          disabled={loading || (mode === 'text' ? !text.trim() : !imageFile)}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (mode === 'image' ? 'Running OCR...' : 'Matching...') : 'Generate Cart'}
        </button>
        <button
          onClick={() => { setText(''); setResults(null); setError(''); setImageFile(null); setImagePreview(null); setOcrRawText(''); }}
          className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Clear
        </button>
      </div>

      {results && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-800">Results ({results.cart_items.length} items)</h2>
            {results.requires_approval && <span className="text-xs text-yellow-700 bg-yellow-100 px-2 py-1 rounded font-medium">⚠ Review required</span>}
          </div>
          <div className="space-y-2 mb-6">
            {results.cart_items.map((item, idx) => (
              <div key={idx} className={`flex items-start gap-4 p-4 border rounded-lg ${rowBg(item.match_type)}`}>
                <div className="min-w-[3rem] text-center">
                  <span className="text-lg font-bold text-gray-700">{item.quantity}</span>
                  <div className="text-xs text-gray-400">qty</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-0.5">
                    {item.product
                      ? <span className="font-medium text-gray-900">{item.product.name}</span>
                      : <span className="font-medium text-gray-400 italic">No product found</span>
                    }
                    {matchBadge(item.match_type, item.confidence)}
                  </div>
                  <div className="text-xs text-gray-500">Input: <span className="font-mono">{item.original_text}</span></div>
                  {item.product && (
                    <div className="text-xs text-gray-500 mt-0.5">
                      {item.product.category} &bull; ${item.product.unit_price.toFixed(2)} / {item.product.unit}
                      {!item.product.in_stock && <span className="ml-2 text-red-500 font-medium">Out of stock</span>}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          {matchedCount > 0 ? (
            <div className="border-t pt-4">
              <p className="text-sm text-gray-600 mb-3">
                {matchedCount} of {results.cart_items.length} item{results.cart_items.length !== 1 ? 's' : ''} matched.
                {matchedCount < results.cart_items.length && ' Unmatched items will be skipped.'}
              </p>
              <button onClick={handleApprove} className="px-6 py-2.5 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors">
                Approve &amp; Add {matchedCount} Item{matchedCount !== 1 ? 's' : ''} to Cart
              </button>
            </div>
          ) : (
            <div className="text-sm text-gray-500 italic">No items could be matched to products in the catalogue.</div>
          )}
        </div>
      )}
    </div>
  );
}
