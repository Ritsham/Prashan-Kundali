import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { bookingApi } from '../../api/bookingApi';
import type { BookingPayload } from '../../api/bookingApi';
import { prashnaApi } from '../../api/prashnaApi';
import { Search, MapPin } from 'lucide-react';
import KundaliChartWrapper from '../../components/charts/KundaliChartWrapper';
import { buildDirectConsultationPayload, buildPrashnaConsultationPayload } from './utils/snapshot';

const notAvailable = 'Not available';

const formatDateTime = (value?: string) => {
  if (!value) return { date: '', time: '' };
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return { date: '', time: '' };
  return {
    date: parsed.toISOString().slice(0, 10),
    time: parsed.toTimeString().slice(0, 5),
  };
};

const interpretationText = (interpretation: any) => {
  if (!interpretation) return '';
  if (typeof interpretation === 'string') return interpretation;
  return interpretation.answer?.text || interpretation.verdict?.summary || interpretation.title || '';
};

const displayValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return notAvailable;
  return String(value);
};

const idempotencyPart = (value: unknown) =>
  String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9@._:-]+/g, '-')
    .slice(0, 32);

const BookingForm: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Extract the snapshot from navigation state
  const { snapshot } = (location.state as any) || {};
  const chart = snapshot?.result?.chart;
  const questionContext = chart?.question || {};
  const questionDateTime = formatDateTime(questionContext.asked_at_local || questionContext.asked_at_utc);
  const hasPrashnaSnapshot = Boolean(snapshot?.result && snapshot?.formData);
  const mainChartData = chart?.signs || chart?.divisional_charts?.D1;

  const [formData, setFormData] = useState<Partial<BookingPayload>>({
    name: snapshot?.formData?.name || '',
    phone: '',
    email: '',
    date_of_birth: questionDateTime.date,
    time_of_birth: questionDateTime.time,
    place_of_birth: snapshot?.formData?.location?.place_name || questionContext.place_name || '',
    latitude: snapshot?.formData?.location?.latitude ?? questionContext.latitude ?? null,
    longitude: snapshot?.formData?.location?.longitude ?? questionContext.longitude ?? null,
    topic: snapshot ? 'Prashna' : 'Other',
    question: snapshot?.formData?.question || '',
    gender: '',
    preferred_date: '',
    preferred_time: '',
    consultation_mode: '',
    additional_message: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<{ message: string; caseId?: string } | null>(null);

  // Location search state
  const [locationSearch, setLocationSearch] = useState(formData.place_of_birth || '');
  const [places, setPlaces] = useState<any[]>([]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const searchPlace = async () => {
    if (locationSearch.length < 2) return;
    try {
      const data = await prashnaApi.geocodePlace(locationSearch);
      setPlaces(data.results || []);
    } catch (err) {
      console.error(err);
    }
  };

  const selectPlace = (place: any) => {
    setFormData({
      ...formData,
      place_of_birth: place.place_name,
      latitude: parseFloat(place.latitude),
      longitude: parseFloat(place.longitude),
    });
    setPlaces([]);
    setLocationSearch(place.place_name);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError('');

    if (!hasPrashnaSnapshot) {
      const missingBirthDetails =
        !formData.date_of_birth ||
        !formData.time_of_birth ||
        !formData.place_of_birth ||
        formData.latitude === null ||
        formData.latitude === undefined ||
        formData.longitude === null ||
        formData.longitude === undefined;
      if (missingBirthDetails) {
        setError('Please select birth date, birth time, and a searched birth place so the Kundli snapshot can be calculated.');
        setIsSubmitting(false);
        return;
      }
    }

    try {
      if (hasPrashnaSnapshot) {
        const idempotencyKey = [
          'prashna',
          snapshot.result.chart_id || chart?.id || 'chart',
          formData.email || 'email',
          formData.phone || 'phone',
        ].join(':');

        const payload = buildPrashnaConsultationPayload({
          result: snapshot.result,
          formData: snapshot.formData,
          user: {
            full_name: formData.name || '',
            email: formData.email || '',
            mobile_number: formData.phone || '',
            date_of_birth: formData.date_of_birth,
            time_of_birth: formData.time_of_birth,
            place: formData.place_of_birth,
            latitude: formData.latitude,
            longitude: formData.longitude,
            timezone: questionContext.timezone,
          },
          additional_message: formData.additional_message,
          preferred_date: formData.preferred_date,
          preferred_time: formData.preferred_time,
          consultation_mode: formData.consultation_mode,
          payment_status: formData.payment_status || 'not_paid',
          idempotency_key: idempotencyKey,
        });

        const result = await bookingApi.createConsultationCase(payload);
        setSuccess({
          message: result.duplicate
            ? 'This consultation case was already submitted. We kept the existing case for the astrologer.'
            : result.message || 'Your consultation case has been successfully submitted.',
          caseId: result.case?.case_id,
        });
      } else {
        const directPayload = buildDirectConsultationPayload({
          formData,
          idempotency_key: [
            'direct',
            idempotencyPart(formData.email),
            idempotencyPart(formData.phone),
            idempotencyPart(formData.date_of_birth),
            idempotencyPart(formData.time_of_birth),
            idempotencyPart(formData.place_of_birth),
          ].join(':').slice(0, 120),
        });
        const result = await bookingApi.createConsultationCase(directPayload);
        setSuccess({
          message: result.duplicate
            ? 'This consultation case was already submitted. We kept the existing case for the astrologer.'
            : result.message || 'Your consultation request has been successfully submitted! We will contact you soon.',
          caseId: result.case?.case_id,
        });
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit booking request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="bg-green-50 text-green-800 p-8 rounded-2xl border border-green-200 text-center">
        <h3 className="text-2xl font-bold mb-4">Success!</h3>
        <p className="mb-2">{success.message}</p>
        {success.caseId && <p className="mb-6 text-sm font-medium">Case ID: {success.caseId}</p>}
        <button 
          onClick={() => navigate('/')}
          className="bg-green-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-green-700"
        >
          Return Home
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm">{error}</div>}

      {hasPrashnaSnapshot && (
        <section className="rounded-xl border border-purple-100 dark:border-purple-800 bg-purple-50/70 dark:bg-purple-900/20 p-4 md:p-5">
          <div className="mb-4">
            <h3 className="text-lg font-bold text-purple-900 dark:text-purple-200">Review Attached Prashna Kundli</h3>
            <p className="text-sm text-purple-800 dark:text-purple-300">
              This exact chart, interpretation, positions, divisional charts, dashas, and available calculations will be sent to the astrologer.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div><strong>User name:</strong> {displayValue(snapshot.formData?.name)}</div>
            <div><strong>Original question:</strong> {displayValue(snapshot.formData?.question)}</div>
            <div><strong>Prashna date:</strong> {displayValue(formData.date_of_birth)}</div>
            <div><strong>Prashna time:</strong> {displayValue(formData.time_of_birth)}</div>
            <div><strong>Location:</strong> {displayValue(formData.place_of_birth)}</div>
            <div><strong>Timezone:</strong> {displayValue(questionContext.timezone)}</div>
            <div><strong>Latitude:</strong> {displayValue(formData.latitude)}</div>
            <div><strong>Longitude:</strong> {displayValue(formData.longitude)}</div>
          </div>

          {mainChartData && (
            <div className="mt-5 rounded-lg border border-purple-100 dark:border-purple-800 bg-white dark:bg-gray-900 p-3">
              <h4 className="mb-3 text-sm font-bold text-gray-700 dark:text-gray-200">Main Prashna Chart</h4>
              <KundaliChartWrapper data={mainChartData} className="max-w-[360px]" />
            </div>
          )}

          <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <div className="rounded-lg bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 p-3">
              <strong>Divisional charts</strong>
              <p>{chart?.divisional_charts ? Object.keys(chart.divisional_charts).join(', ') : notAvailable}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 p-3">
              <strong>Planetary positions</strong>
              <p>{Array.isArray(chart?.planets) ? `${chart.planets.length} planets attached` : notAvailable}</p>
            </div>
            <div className="rounded-lg bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 p-3">
              <strong>Dashas</strong>
              <p>{chart?.dashas ? 'Attached' : notAvailable}</p>
            </div>
          </div>

          {interpretationText(snapshot.result?.interpretation || chart?.interpretation) && (
            <details className="mt-5 rounded-lg bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 p-3">
              <summary className="cursor-pointer text-sm font-bold">Generated interpretation</summary>
              <div className="mt-3 max-h-56 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed">
                {interpretationText(snapshot.result?.interpretation || chart?.interpretation)}
              </div>
            </details>
          )}
        </section>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input required type="text" name="name" value={formData.name} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input required type="email" name="email" value={formData.email} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Phone Number</label>
          <input required type="tel" name="phone" value={formData.phone} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Topic</label>
          <select name="topic" value={formData.topic} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700">
            <option value="Prashna">Prashna (Current Question)</option>
            <option value="Birth Chart">Birth Chart Reading</option>
            <option value="Matchmaking">Matchmaking</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Gender</label>
          <select name="gender" value={formData.gender || ''} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700">
            <option value="">Prefer not to say</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium mb-1">{formData.topic === 'Prashna' ? 'Date of Question' : 'Date of Birth'}</label>
          <input type="date" name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">{formData.topic === 'Prashna' ? 'Time of Question' : 'Time of Birth'}</label>
          <input type="time" name="time_of_birth" value={formData.time_of_birth} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">{formData.topic === 'Prashna' ? 'Place of Question' : 'Place of Birth'}</label>
        <div className="flex gap-2">
          <div className="relative flex-grow">
            <input 
              type="text" 
              value={locationSearch}
              onChange={(e) => setLocationSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), searchPlace())}
              className="w-full p-3 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" 
              placeholder="Type city name..."
            />
            <Search className="absolute left-3 top-3.5 text-gray-400" size={18} />
          </div>
          <button type="button" onClick={searchPlace} className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg flex items-center gap-2">
            <MapPin size={18} /> Search
          </button>
        </div>
        {places.length > 0 && (
          <div className="mt-2 border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden divide-y divide-gray-200 dark:divide-gray-700">
            {places.map((place, idx) => (
              <button key={idx} type="button" onClick={() => selectPlace(place)} className="w-full text-left p-3 hover:bg-gray-50 dark:hover:bg-gray-700">
                <span className="font-medium">{place.place_name}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Your Question / Details</label>
        <textarea required name="question" value={formData.question} onChange={handleChange} rows={4} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" placeholder="Please describe what you want to consult about..."></textarea>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Additional Message for Astrologer</label>
        <textarea name="additional_message" value={formData.additional_message || ''} onChange={handleChange} rows={3} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" placeholder="Add any extra context you want the astrologer to know..."></textarea>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium mb-1">Preferred Consultation Date</label>
          <input type="date" name="preferred_date" value={formData.preferred_date || ''} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Preferred Time</label>
          <input type="time" name="preferred_time" value={formData.preferred_time || ''} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700" />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Consultation Mode</label>
          <select name="consultation_mode" value={formData.consultation_mode || ''} onChange={handleChange} className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700">
            <option value="">No preference</option>
            <option value="phone">Phone</option>
            <option value="video">Video call</option>
            <option value="chat">Chat</option>
          </select>
        </div>
      </div>

      {snapshot && (
        <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg text-sm text-purple-800 dark:text-purple-300 flex items-center gap-3 border border-purple-100 dark:border-purple-800">
          <div className="w-2 h-2 rounded-full bg-purple-500 flex-shrink-0 animate-pulse" />
          <p>Your Prashna Kundli chart and interpretation snapshot will be automatically sent to the astrologer along with this request.</p>
        </div>
      )}

      <button type="submit" disabled={isSubmitting} className="w-full bg-purple-600 text-white py-3 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 transition">
        {isSubmitting ? 'Submitting Request...' : 'Book Consultation'}
      </button>
    </form>
  );
};

export default BookingForm;
