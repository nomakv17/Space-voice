 "use client";
 
 import { BarChart3, CheckCircle2 } from "lucide-react";
 
 const caseStudies = [
   {
     company: "CoolAir HVAC Solutions",
     location: "Phoenix, AZ",
     outcome: "$8,500/mo recovered",
     before: [
       "After-hours calls to voicemail",
       "No consistent emergency triage",
       "Manual scheduling follow-up",
     ],
     after: [
       "24/7 AI call coverage",
       "Emergency escalations routed instantly",
       "Calendar bookings + SMS confirmations",
     ],
   },
   {
     company: "SafeHome Plumbing",
     location: "Dallas, TX",
     outcome: "100% critical issue detection",
     before: [
       "High-volume calls during emergencies",
       "Dispatch team overwhelmed",
       "Lost urgency context on handoff",
     ],
     after: [
       "Structured safety triage every call",
       "Priority alerts with context",
       "Faster dispatch decisions",
     ],
   },
   {
     company: "Thompson Electric",
     location: "Atlanta, GA",
     outcome: "73% booking rate increase",
     before: [
       "Missed callbacks on evenings",
       "Inconsistent lead capture",
       "Low booking conversion",
     ],
     after: [
       "Instant call capture",
       "Consistent contact collection",
       "Automated scheduling flow",
     ],
   },
 ];
 
 export function CaseStudiesSection() {
   return (
     <section className="relative py-24 bg-gray-50">
       <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
         <div className="text-center mb-14">
           <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-gray-200 text-gray-600 text-sm font-medium mb-6 shadow-sm">
             Proven Outcomes
           </div>
           <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
             Before &amp; After{" "}
             <span className="bg-gradient-to-r from-cyan-600 to-purple-600 bg-clip-text text-transparent">
               Results
             </span>
           </h2>
           <p className="text-lg text-gray-600 max-w-2xl mx-auto">
             Short, verifiable snapshots showing how SpaceVoice changes outcomes in the first 30
             days.
           </p>
         </div>
 
         <div className="grid lg:grid-cols-3 gap-8">
           {caseStudies.map((study) => (
             <div
               key={study.company}
               className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm hover:shadow-lg transition-all duration-300"
             >
               <div className="flex items-start justify-between mb-6">
                 <div>
                   <h3 className="text-xl font-semibold text-gray-900">{study.company}</h3>
                   <p className="text-sm text-gray-500">{study.location}</p>
                 </div>
                 <div className="flex items-center gap-2 text-cyan-600">
                   <BarChart3 className="h-5 w-5" />
                   <span className="text-sm font-semibold">{study.outcome}</span>
                 </div>
               </div>
 
               <div className="mb-6">
                 <p className="text-xs uppercase tracking-wide text-gray-400 mb-3">Before</p>
                 <ul className="space-y-2 text-sm text-gray-600">
                   {study.before.map((item) => (
                     <li key={item} className="flex items-start gap-2">
                       <span className="mt-1 h-1.5 w-1.5 rounded-full bg-gray-400" />
                       {item}
                     </li>
                   ))}
                 </ul>
               </div>
 
               <div>
                 <p className="text-xs uppercase tracking-wide text-gray-400 mb-3">After</p>
                 <ul className="space-y-2 text-sm text-gray-700">
                   {study.after.map((item) => (
                     <li key={item} className="flex items-start gap-2">
                       <CheckCircle2 className="h-4 w-4 text-cyan-600 mt-0.5" />
                       {item}
                     </li>
                   ))}
                 </ul>
               </div>
             </div>
           ))}
         </div>
       </div>
     </section>
   );
 }
