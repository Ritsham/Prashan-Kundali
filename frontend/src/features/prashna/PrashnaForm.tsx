import React, { useState } from 'react';
import { prashnaApi } from '../../api/prashnaApi';
import type { PrashnaPayload } from '../../types/prashna';
import { MapPin, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const PrashnaForm: React.FC = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<Partial<PrashnaPayload>>({
    name: '',
    question: '',
    question_domain: '',
    question_subdomain: '',
  });
  const [locationSearch, setLocationSearch] = useState('');
  const [places, setPlaces] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const navigate = useNavigate();

  const handleNext = () => setStep((s) => Math.min(s + 1, 3));
  const handleBack = () => setStep((s) => Math.max(s - 1, 1));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const searchPlace = async () => {
    if (locationSearch.length < 2) return;
    setIsSearching(true);
    try {
      const data = await prashnaApi.geocodePlace(locationSearch);
      setPlaces(data.results || []);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch places');
    } finally {
      setIsSearching(false);
    }
  };

  const selectPlace = (place: any) => {
    setFormData({
      ...formData,
      location: {
        latitude: parseFloat(place.latitude),
        longitude: parseFloat(place.longitude),
        place_name: place.place_name,
      }
    });
    setPlaces([]);
    setLocationSearch(place.place_name);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name || !formData.question || !formData.location) {
      setError('Please fill in all required fields including location.');
      return;
    }

    setIsGenerating(true);
    try {
      const result = await prashnaApi.generatePrashna(formData as PrashnaPayload);
      // Pass the result to the result page (via state or context in the future)
      navigate('/prashna-result', { state: { result, formData } });
    } catch (err: any) {
      setError(err.message || 'Failed to generate Prashna');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 md:p-8">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex justify-between text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
          <span className={step >= 1 ? 'text-purple-600' : ''}>Personal</span>
          <span className={step >= 2 ? 'text-purple-600' : ''}>Details</span>
          <span className={step >= 3 ? 'text-purple-600' : ''}>Location</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div 
            className="bg-purple-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(step / 3) * 100}%` }}
          />
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}

        {/* Step 1 */}
        <div className={step === 1 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input 
                type="text" 
                name="name"
                value={formData.name}
                onChange={handleChange}
                required 
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 focus:ring-2 focus:ring-purple-500" 
                placeholder="Your name"
              />
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button type="button" onClick={handleNext} disabled={!formData.name} className="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50">
              Next Step
            </button>
          </div>
        </div>

        {/* Step 2 */}
        <div className={step === 2 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Question</label>
              <textarea 
                name="question"
                value={formData.question}
                onChange={handleChange}
                required 
                rows={4}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 focus:ring-2 focus:ring-purple-500" 
                placeholder="Ask the exact Prashna question"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Question Domain</label>
              <select 
                name="question_domain"
                value={formData.question_domain}
                onChange={handleChange}
                className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 focus:ring-2 focus:ring-purple-500"
              >
                <option value="">General / not sure</option>
                <option value="wealth">Wealth / money</option>
                <option value="marriage">Marriage / relationship</option>
                <option value="child">Child / progeny</option>
                <option value="job_career">Job / career</option>
                <option value="illness">Illness / health</option>
                <option value="foreign">Foreign / travel</option>
                <option value="education">Education</option>
              </select>
            </div>
            {formData.question_domain === 'job_career' && (
              <div>
                <label className="block text-sm font-medium mb-1">Job Type</label>
                <select 
                  name="question_subdomain"
                  value={formData.question_subdomain}
                  onChange={handleChange}
                  className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Not sure</option>
                  <option value="government">Government job</option>
                  <option value="private">Private job</option>
                </select>
              </div>
            )}
          </div>
          <div className="mt-6 flex justify-between">
            <button type="button" onClick={handleBack} className="bg-gray-200 dark:bg-gray-700 px-6 py-2 rounded-lg font-medium hover:bg-gray-300 dark:hover:bg-gray-600">
              Back
            </button>
            <button type="button" onClick={handleNext} disabled={!formData.question} className="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50">
              Next Step
            </button>
          </div>
        </div>

        {/* Step 3 */}
        <div className={step === 3 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">City / Place</label>
              <div className="flex gap-2">
                <div className="relative flex-grow">
                  <input 
                    type="text" 
                    value={locationSearch}
                    onChange={(e) => setLocationSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchPlace())}
                    className="w-full p-3 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 focus:ring-2 focus:ring-purple-500" 
                    placeholder="Type city name..."
                  />
                  <Search className="absolute left-3 top-3.5 text-gray-400" size={18} />
                </div>
                <button type="button" onClick={searchPlace} className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2">
                  <MapPin size={18} /> Search
                </button>
              </div>
              
              {/* Search Results */}
              {places.length > 0 && (
                <div className="mt-2 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden divide-y divide-gray-200 dark:divide-gray-700">
                  {places.map((place, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => selectPlace(place)}
                      className="w-full text-left p-3 hover:bg-gray-50 dark:hover:bg-gray-700 flex flex-col"
                    >
                      <span className="font-medium">{place.place_name}</span>
                      <span className="text-xs text-gray-500">{place.latitude}, {place.longitude} &middot; {place.source}</span>
                    </button>
                  ))}
                </div>
              )}
              {isSearching && <p className="text-sm mt-2 text-gray-500">Searching...</p>}
            </div>
            
            <details className="mt-4 text-sm group">
              <summary className="cursor-pointer text-purple-600 font-medium list-none flex items-center gap-2">
                <span>Manual coordinates</span>
                <span className="transition group-open:rotate-180">&darr;</span>
              </summary>
              <div className="mt-4 space-y-4 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
                 <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium mb-1">Latitude</label>
                      <input 
                        type="number" step="any"
                        value={formData.location?.latitude || ''}
                        onChange={(e) => setFormData({...formData, location: { ...formData.location!, latitude: parseFloat(e.target.value) }})}
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" 
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Longitude</label>
                      <input 
                        type="number" step="any"
                        value={formData.location?.longitude || ''}
                        onChange={(e) => setFormData({...formData, location: { ...formData.location!, longitude: parseFloat(e.target.value) }})}
                        className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" 
                      />
                    </div>
                 </div>
                 <div>
                    <label className="block text-xs font-medium mb-1">Place name</label>
                    <input 
                      type="text"
                      value={formData.location?.place_name || ''}
                      onChange={(e) => setFormData({...formData, location: { ...formData.location!, place_name: e.target.value }})}
                      className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" 
                    />
                 </div>
              </div>
            </details>
          </div>
          <div className="mt-6 flex justify-between">
            <button type="button" onClick={handleBack} className="bg-gray-200 dark:bg-gray-700 px-6 py-2 rounded-lg font-medium hover:bg-gray-300 dark:hover:bg-gray-600">
              Back
            </button>
            <button type="submit" disabled={isGenerating || !formData.location} className="bg-purple-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-purple-700 flex items-center gap-2 disabled:opacity-50">
              {isGenerating ? 'Generating...' : 'Generate Kundli'}
            </button>
          </div>
        </div>

      </form>
    </div>
  );
};

export default PrashnaForm;
