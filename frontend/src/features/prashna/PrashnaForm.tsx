import React, { useState } from 'react';
import { prashnaApi } from '../../api/prashnaApi';
import type { PrashnaPayload } from '../../types/prashna';
import { MapPin, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiErrorMessage } from '../../api/errors';
import { boundedText, validCoordinate } from '../../utils/validation';

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

  const handleNext = () => {
    setError('');
    if (step === 1 && !boundedText(formData.name, 1, 80)) {
      setError('Name must be between 1 and 80 characters.');
      return;
    }
    if (step === 2 && !boundedText(formData.question, 3, 1000)) {
      setError('Question must be between 3 and 1000 characters.');
      return;
    }
    setStep((s) => Math.min(s + 1, 3));
  };
  const handleBack = () => setStep((s) => Math.max(s - 1, 1));

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const searchPlace = async () => {
    if (locationSearch.trim().length < 2) {
      setError('Enter at least 2 characters to search a place.');
      return;
    }
    setError('');
    setIsSearching(true);
    try {
      const data = await prashnaApi.geocodePlace(locationSearch);
      setPlaces(data.results || []);
      if (!data.results?.length) setError('No places found. Try a nearby city or enter coordinates manually.');
    } catch (err) {
      setError(apiErrorMessage(err));
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

  const updateManualLocation = (patch: Partial<NonNullable<PrashnaPayload['location']>>) => {
    setFormData({
      ...formData,
      location: {
        latitude: formData.location?.latitude ?? 0,
        longitude: formData.location?.longitude ?? 0,
        place_name: formData.location?.place_name || locationSearch || 'Manual location',
        ...patch,
      },
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!boundedText(formData.name, 1, 80)) {
      setError('Name must be between 1 and 80 characters.');
      return;
    }
    if (!boundedText(formData.question, 3, 1000)) {
      setError('Question must be between 3 and 1000 characters.');
      return;
    }
    if (!formData.location || !formData.location.place_name || !validCoordinate(formData.location.latitude, formData.location.longitude)) {
      setError('Please select a valid location with latitude and longitude.');
      return;
    }

    setIsGenerating(true);
    try {
      const result = await prashnaApi.generatePrashna(formData as PrashnaPayload);
      // Pass the result to the result page (via state or context in the future)
      navigate('/prashna-result', { state: { result, formData } });
    } catch (err) {
      setError(apiErrorMessage(err));
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
      {error && <div className="app-alert app-alert--error" role="alert">{error}</div>}

        {/* Step 1 */}
        <div className={step === 1 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="form-label" htmlFor="prashna-name">Name</label>
              <input 
                id="prashna-name"
                type="text" 
                name="name"
                value={formData.name}
                onChange={handleChange}
                required 
                maxLength={80}
                className="form-control"
                placeholder="Your name"
              />
            </div>
          </div>
          <div className="mt-6 action-row action-row--end">
            <button type="button" onClick={handleNext} disabled={!formData.name} className="btn-primary">
              Next Step
            </button>
          </div>
        </div>

        {/* Step 2 */}
        <div className={step === 2 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="form-label" htmlFor="prashna-question">Question</label>
              <textarea 
                id="prashna-question"
                name="question"
                value={formData.question}
                onChange={handleChange}
                required 
                rows={4}
                maxLength={1000}
                className="form-control"
                placeholder="Ask the exact Prashna question"
              />
            </div>
            <div>
              <label className="form-label" htmlFor="prashna-domain">Question Domain</label>
              <select 
                id="prashna-domain"
                name="question_domain"
                value={formData.question_domain}
                onChange={handleChange}
                className="form-control"
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
                <label className="form-label" htmlFor="prashna-subdomain">Job Type</label>
                <select 
                  id="prashna-subdomain"
                  name="question_subdomain"
                  value={formData.question_subdomain}
                  onChange={handleChange}
                  className="form-control"
                >
                  <option value="">Not sure</option>
                  <option value="government">Government job</option>
                  <option value="private">Private job</option>
                </select>
              </div>
            )}
          </div>
          <div className="mt-6 action-row">
            <button type="button" onClick={handleBack} className="btn-secondary">
              Back
            </button>
            <button type="button" onClick={handleNext} disabled={!formData.question} className="btn-primary">
              Next Step
            </button>
          </div>
        </div>

        {/* Step 3 */}
        <div className={step === 3 ? 'block' : 'hidden'}>
          <div className="space-y-4">
            <div>
              <label className="form-label" htmlFor="prashna-place">City / Place</label>
              <div className="responsive-search-row">
                <div className="relative flex-grow">
                  <input 
                    id="prashna-place"
                    type="text" 
                    value={locationSearch}
                    onChange={(e) => setLocationSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchPlace())}
                    className="form-control pl-10"
                    placeholder="Type city name..."
                  />
                  <Search className="absolute left-3 top-3.5 text-gray-400" size={18} />
                </div>
                <button type="button" onClick={searchPlace} disabled={isSearching} className="btn-secondary inline-flex items-center justify-center gap-2">
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
                        onChange={(e) => updateManualLocation({ latitude: Number(e.target.value) })}
                        className="form-control"
                        min={-90}
                        max={90}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">Longitude</label>
                      <input 
                        type="number" step="any"
                        value={formData.location?.longitude || ''}
                        onChange={(e) => updateManualLocation({ longitude: Number(e.target.value) })}
                        className="form-control"
                        min={-180}
                        max={180}
                      />
                    </div>
                 </div>
                 <div>
                    <label className="block text-xs font-medium mb-1">Place name</label>
                    <input 
                      type="text"
                      value={formData.location?.place_name || ''}
                      onChange={(e) => updateManualLocation({ place_name: e.target.value })}
                      className="form-control"
                    />
                 </div>
              </div>
            </details>
          </div>
          <div className="mt-6 action-row">
            <button type="button" onClick={handleBack} className="btn-secondary">
              Back
            </button>
            <button type="submit" disabled={isGenerating || !formData.location} className="btn-primary inline-flex items-center justify-center gap-2">
              {isGenerating ? 'Generating...' : 'Generate Kundli'}
            </button>
          </div>
        </div>

      </form>
    </div>
  );
};

export default PrashnaForm;
