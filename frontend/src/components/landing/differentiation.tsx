 "use client";
 
 import { Shield, CalendarCheck, PhoneCall, Zap } from "lucide-react";
 
 const differentiators = [
   {
     icon: Shield,
     title: "Safety-First Triage",
     description:
       "Detects urgent risks like gas leaks and escalates immediately while keeping the caller calm.",
     proof: "Built for HVAC and home services, not generic chatbots.",
   },
   {
     icon: CalendarCheck,
     title: "Real-Time Booking",
     description:
       "Checks availability and books confirmed appointments directly into your calendar.",
     proof: "No double-bookings or manual follow-up.",
   },
   {
     icon: PhoneCall,
     title: "Human-Quality Conversations",
     description:
       "Natural pacing, clear questions, and zero dead ends even during interruptions.",
     proof: "Designed to sound like your best receptionist.",
   },
   {
     icon: Zap,
     title: "Immediate ROI",
     description:
       "Recover missed calls and convert after-hours leads without adding staff.",
     proof: "Most customers see results in the first week.",
   },
 ];
 
 export function DifferentiationSection() {
   return (
     <section id="why-spacevoice" className="relative py-24 bg-white">
       <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
         <div className="text-center mb-14">
           <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gray-100 border border-gray-200 text-gray-600 text-sm font-medium mb-6">
             Why SpaceVoice
           </div>
           <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
             Built to{" "}
             <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
               Outperform
             </span>{" "}
             Answering Services
           </h2>
           <p className="text-lg text-gray-600 max-w-2xl mx-auto">
             A purpose-built voice agent that converts calls into bookings while staying safe,
             fast, and human-like.
           </p>
         </div>
 
         <div className="grid md:grid-cols-2 gap-8">
           {differentiators.map((item) => {
             const Icon = item.icon;
             return (
               <div
                 key={item.title}
                 className="group rounded-2xl border border-gray-200 bg-gray-50 p-8 transition-all duration-300 hover:border-cyan-200 hover:shadow-lg"
               >
                 <div className="flex items-center gap-3 mb-4">
                   <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-cyan-600 shadow-sm">
                     <Icon className="h-6 w-6" />
                   </div>
                   <h3 className="text-xl font-semibold text-gray-900">{item.title}</h3>
                 </div>
                 <p className="text-gray-600 mb-4">{item.description}</p>
                 <p className="text-sm text-gray-500">{item.proof}</p>
               </div>
             );
           })}
         </div>
       </div>
     </section>
   );
 }
