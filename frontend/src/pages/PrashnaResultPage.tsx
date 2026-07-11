import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import KundaliChartWrapper from '../components/charts/KundaliChartWrapper';

const PrashnaResultPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'interpretation' | 'charts'>('interpretation');

  // result and formData are passed via router state from the PrashnaForm
  const { result, formData } = (location.state as any) || {};

  if (!result) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <h2 className="text-2xl font-bold mb-4">No Result Found</h2>
        <p className="text-gray-600 mb-6">It looks like you haven't generated a Prashna Kundli yet.</p>
        <button 
          onClick={() => navigate('/prashna')}
          className="bg-purple-600 text-white px-6 py-2 rounded-lg"
        >
          Go Back
        </button>
      </div>
    );
  }

  const { chart, interpretation } = result;

  const handleBookConsultation = () => {
    navigate('/booking', { state: { snapshot: { result, formData } } });
  };

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Prashna Kundli Result</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Question: <span className="font-medium text-gray-900 dark:text-gray-100">{formData?.question || 'N/A'}</span>
        </p>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 mb-6">
        <button
          onClick={() => setActiveTab('interpretation')}
          className={`py-3 px-6 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'interpretation'
              ? 'border-purple-600 text-purple-600 dark:border-purple-400 dark:text-purple-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Interpretation
        </button>
        <button
          onClick={() => setActiveTab('charts')}
          className={`py-3 px-6 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'charts'
              ? 'border-purple-600 text-purple-600 dark:border-purple-400 dark:text-purple-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
          }`}
        >
          Charts & Positions
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 md:p-8">
        
        {/* Interpretation Tab */}
        {activeTab === 'interpretation' && (
          <div className="space-y-8">
            <div className="prose dark:prose-invert max-w-none">
              {interpretation ? (
                // Properly rendering LLM formatted text (assuming it might have markdown or paragraphs)
                <div 
                  className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-wrap"
                  dangerouslySetInnerHTML={{ __html: interpretation }} 
                />
              ) : (
                <p className="text-gray-500 italic">No interpretation available.</p>
              )}
            </div>

            <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700 text-center bg-purple-50 dark:bg-purple-900/20 p-8 rounded-xl">
              <h3 className="text-xl font-bold mb-2">Need Deeper Insights?</h3>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Consult an Astrologer for a detailed and personalized analysis of this chart.
              </p>
              <button 
                onClick={handleBookConsultation}
                className="bg-purple-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-purple-700 transition"
              >
                Book Consultation
              </button>
            </div>
          </div>
        )}

        {/* Charts & Positions Tab */}
        {activeTab === 'charts' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Left: Visual Chart */}
            <div className="flex flex-col items-center border border-gray-200 dark:border-gray-700 rounded-xl p-4">
              <h3 className="text-lg font-bold mb-4">Prashna Kundli (Lagna)</h3>
              {chart?.signs ? (
                <KundaliChartWrapper data={chart.signs} />
              ) : (
                <div className="aspect-square flex items-center justify-center text-gray-400 bg-gray-50 dark:bg-gray-900 w-full rounded-lg">
                  Chart Data Unavailable
                </div>
              )}
            </div>

            {/* Right: Positions Data */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">Planetary Positions</h3>
                {chart?.planets ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="bg-gray-50 dark:bg-gray-900 text-gray-500">
                        <tr>
                          <th className="px-3 py-2">Planet</th>
                          <th className="px-3 py-2">Sign</th>
                          <th className="px-3 py-2">Degree</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                        {Object.entries(chart.planets).map(([planet, details]: [string, any]) => (
                          <tr key={planet}>
                            <td className="px-3 py-2 font-medium">{planet}</td>
                            <td className="px-3 py-2">{details.sign || '-'}</td>
                            <td className="px-3 py-2 text-gray-500">{details.normDegree?.toFixed(2) || '-'}°</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No planetary data available.</p>
                )}
              </div>

              {chart?.ascendant && (
                <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                  <h4 className="font-semibold text-sm text-gray-500 uppercase tracking-wider mb-1">Ascendant (Lagna)</h4>
                  <p className="text-lg font-medium">{chart.ascendant.sign} ({chart.ascendant.normDegree?.toFixed(2)}°)</p>
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

export default PrashnaResultPage;
