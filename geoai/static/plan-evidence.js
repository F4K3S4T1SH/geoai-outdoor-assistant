'use strict';
(function(root){
  function windowMetrics(option){
    const samples=option.hourly_evidence?.length?option.hourly_evidence:[{weather:option.weather||{},us_aqi:option.us_aqi,time:option.time}];
    const fields={temperature:s=>s.weather?.apparent_temperature,rain:s=>s.weather?.precipitation_probability,aqi:s=>s.us_aqi,wind:s=>s.weather?.wind_speed_10m};
    const result={samples,partial:false};
    for(const [key,read]of Object.entries(fields)){
      const values=samples.map(read);const available=values.filter(v=>typeof v==='number'&&Number.isFinite(v));
      result[key]=available.length?Math.max(...available):null;
      if(available.length!==values.length)result.partial=true;
    }
    return result;
  }
  function representativeFailures(options,limit=2){
    const selected=[],signatures=new Set();
    for(const option of options){
      const signature=[...(option.condition_reasons||[]),...(option.checks_missing||[]),...(option.condition_reasons?[]:option.avoid_reasons||[])].sort().join('|');
      if(!signatures.has(signature)){selected.push(option);signatures.add(signature);}
      if(selected.length===limit)return selected;
    }
    for(const option of options){if(!selected.includes(option))selected.push(option);if(selected.length===limit)break;}
    return selected;
  }
  const api={windowMetrics,representativeFailures};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OutsideEvidence=api;
})(typeof globalThis!=='undefined'?globalThis:this);
