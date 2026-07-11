import React from 'react';
import BookingForm from '../features/consultation/BookingForm';

const BookingPage: React.FC = () => {
  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-4">Book a Consultation</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Connect with expert astrologers to get personalized insights and guidance.
        </p>
      </div>
      
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 md:p-8">
        <BookingForm />
      </div>
    </div>
  );
};

export default BookingPage;
