import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';

export default function RetailerList() {
  const [retailers, setRetailers] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      api.get('/retailers', { params: { search } }).then(({ data }) => {
        setRetailers(data);
        setLoading(false);
      });
    }, 200);
    return () => clearTimeout(timer);
  }, [search]);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">My Retailers</h1>
      <input
        type="text"
        placeholder="Search retailers..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full border border-gray-300 rounded-md px-4 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : retailers.length === 0 ? (
        <p className="text-gray-500">No retailers found.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {retailers.map((r) => (
            <Link
              key={r.id}
              to={`/retailers/${r.id}`}
              className="block bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-shadow"
            >
              <h2 className="font-semibold text-lg text-gray-900">{r.name}</h2>
              <p className="text-sm text-gray-500 mt-1">{r.address}</p>
              {r.contact_phone && (
                <p className="text-sm text-gray-500">{r.contact_phone}</p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
